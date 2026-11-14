"""YOUR PoC PIPELINE — this is the file your group owns.

Lab contract = 5 automated steps, run by `python -m src.main ...`:
    01 load      input + provenance check (manifest.csv)
    02 process   your algorithm / model (the research part)
    03 rank      prioritise for a fixed review budget B
    04 review    human-in-the-loop: queue -> reviewer decisions -> overrides + audit log
    05 decide    GO / HOLD / REWORK (or track equivalent) with reason_code + owner, write outputs

Required output: out/<pred_file> with the columns listed for your track in
docs/tracks/TXX.md (also in src/metrics/tracks.py::TRACKS). Then evaluate with
    python -m src.evaluate --track tXX --pred out/<pred_file>

Rules: never read fixtures/*/gt/ here (the GT guard will stop you); seed everything via ctx.rng;
no network calls; fail loudly on missing models instead of downloading.
See src/examples/random_baseline.py for a minimal end-to-end wiring example.
"""
from __future__ import annotations

import pandas as pd

from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.manifest import verify_manifest
from .common.review import load_review_decisions, make_review_queue, write_review_queue
from .metrics.tracks import get_track


# ---------------------------------------------------------------- 01 load
def load(ctx: RunContext) -> dict:
    manifest = ctx.input_dir / "manifest.csv"
    problems = verify_manifest(manifest) if manifest.exists() else [{"problem": "no_manifest"}]
    if problems:
        ctx.audit.log(actor="pipeline", action="provenance_problems", item_id=str(manifest), after=problems[:20])
        if ctx.config.get("strict_provenance", True):
            raise ValueError(f"provenance check failed ({len(problems)} problems), first: {problems[:3]}")
    data = {"manifest": pd.read_csv(manifest) if manifest.exists() else None}
    # TODO: load the tables/images your track needs, e.g.
    # data["images"] = pd.read_csv(ctx.input_dir / "images.csv")
    data["images"] = pd.read_csv(ctx.input_dir / "images.csv")
    return data


# ---------------------------------------------------------------- 02 process
def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    from .common.image_ops import laplacian_variance, load_rgb, to_gray

    rows = []
    for row in data["images"].itertuples(index=False):
        image = load_rgb(ctx.input_dir / row.path)
        gray = to_gray(image)

        sharpness = laplacian_variance(gray)
        blur_score = 35.0 / max(sharpness, 0.01)

        # Cảnh đêm có mức sáng kỳ vọng thấp hơn cảnh ban ngày.
        dark_limit = {"day": 45, "dusk": 32, "night": 18}.get(row.light, 45)
        dark_score = dark_limit / max(float(gray.mean()), 1.0)

        # Tìm vùng lóa cục bộ trên lưới 4 × 4.
        height, width = gray.shape
        glare_fraction = max(
            float((gray[y * height // 4:(y + 1) * height // 4,
                        x * width // 4:(x + 1) * width // 4] > 245).mean())
            for y in range(4)
            for x in range(4)
        )
        glare_score = glare_fraction / 0.40

        signals = {"blur": blur_score, "dark": dark_score, "glare": glare_score}
        strongest = max(signals, key=signals.get)
        score = signals[strongest]

        rows.append({
            "image_id": row.image_id,
            "score": score,
            "reason": strongest,
            "pred_defect_type": strongest if score >= 1 else "none",
            "pred_action": "RECAPTURE" if score >= 1 else "KEEP",
            "path": row.path,
            "light": row.light,
            "split": row.split,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 03 rank
def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    from .common.contact_sheet import render_contact_sheet

    eval_images = scored.loc[scored["split"] == "eval"]
    budget = int(ctx.param("budget", 20))

    queue = make_review_queue(
        eval_images,
        id_col="image_id",
        score_col="score",
        budget=budget,
        reason_col="reason",
        action_col="pred_action",
        slice_col="light",
        evidence_col="path",
    )

    write_review_queue(queue, ctx.out("review_queue.csv"))
    render_contact_sheet(
        queue,
        ctx.out("contact_sheet.html"),
        image_root=ctx.input_dir,
        title="T02 – Review 20 ảnh ưu tiên",
    )
    return queue


# ---------------------------------------------------------------- 04 review
def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    from .common.review import apply_overrides

    final = scored.copy()
    final["review_state"] = "not_queued"
    final.loc[final["image_id"].isin(queue["item_id"]), "review_state"] = "pending"

    reviewed_path = ctx.out("review_queue_reviewed.csv")
    if not reviewed_path.exists():
        return final

    reviewed = load_review_decisions(
        reviewed_path, allowed={"approve", "edit", "escalate", "skip"}
    )
    if reviewed["item_id"].duplicated().any():
        raise ValueError("CSV review có ID ảnh trùng")
    if not reviewed["item_id"].isin(queue["item_id"]).all():
        raise ValueError("CSV review có ảnh ngoài hàng đợi hiện tại")

    edits = reviewed["reviewer_decision"] == "edit"
    if not reviewed.loc[edits, "override_value"].isin({"KEEP", "RECAPTURE"}).all():
        raise ValueError("Quyết định edit cần override_value là KEEP hoặc RECAPTURE")

    final = apply_overrides(final, reviewed, "image_id", "pred_action", ctx.audit)
    for row in reviewed.itertuples(index=False):
        mask = final["image_id"] == row.item_id
        final.loc[mask, "review_state"] = row.reviewer_decision
        if row.reviewer_decision != "edit":
            ctx.audit.log(
                actor=row.reviewer,
                action=row.reviewer_decision,
                item_id=row.item_id,
                reason=row.review_note,
            )

    ctx.stats["n_reviewed"] = len(reviewed)
    return final


# ---------------------------------------------------------------- 05 decide
def decide(ctx: RunContext, final: pd.DataFrame) -> Decision:
    queued = final.loc[final["review_state"] != "not_queued"]
    resolved = queued["review_state"].isin({"approve", "edit"})
    recapture = int((resolved & (queued["pred_action"] == "RECAPTURE")).sum())

    if queued.empty or not resolved.all():
        status = "HOLD"
        reason_code = "REVIEW_INCOMPLETE"
        reason = "Hàng đợi còn ảnh chưa được giải quyết."
    elif recapture:
        status = "RECAPTURE"
        reason_code = "REVIEW_CONFIRMED_RECAPTURE"
        reason = f"Người duyệt xác nhận {recapture} ảnh cần chụp lại."
    else:
        status = "KEEP"
        reason_code = "REVIEW_ALL_KEEP"
        reason = "Người duyệt đồng ý giữ tất cả ảnh trong hàng đợi."

    return Decision(
        status=status,
        reason_code=reason_code,
        reason=reason,
        owner=ctx.config["owner"],
        scope=ctx.track,
        evidence=["review_queue_reviewed.csv", "audit_log.jsonl", "ranked_review.csv"],
        metrics={"queued": len(queued), "resolved": int(resolved.sum()), "recapture": recapture},
    )


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    data = load(ctx)
    scored = process(ctx, data)
    ctx.stats["n_items"] = len(scored)
    queue = rank(ctx, scored)
    final = review(ctx, scored, queue)
    final[spec.pred_columns + [c for c in final.columns if c not in spec.pred_columns]].to_csv(ctx.out(spec.pred_file), index=False)
    write_decision(decide(ctx, final), ctx.out("decision.json"), ctx.out("decision_log.csv"))
