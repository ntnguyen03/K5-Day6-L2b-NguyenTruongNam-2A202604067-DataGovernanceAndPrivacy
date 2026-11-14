import json

import pandas as pd

from src import main as runner


def run_poc(output):
    return runner.main([
        "--track", "t02", "--output", str(output),
        "--offline", "--seed", "42",
    ])


def prepare_review(output):
    assert run_poc(output) == 0
    queue = pd.read_csv(output / "review_queue.csv", dtype=str).fillna("")
    assert len(queue) == 20
    queue["reviewer"] = "Test reviewer"
    queue["reviewer_decision"] = "approve"
    return queue


def test_t02_applies_and_logs_override(tmp_path):
    queue = prepare_review(tmp_path)
    index = queue.index[queue["suggested_action"].eq("RECAPTURE")][0]
    image_id = queue.at[index, "item_id"]
    queue.loc[index, ["reviewer_decision", "override_value", "review_note"]] = [
        "edit", "KEEP", "Test override",
    ]
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)

    assert run_poc(tmp_path) == 0
    predictions = pd.read_csv(tmp_path / "ranked_review.csv").set_index("image_id")
    assert predictions.at[image_id, "pred_action"] == "KEEP"

    audit = (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in audit.splitlines()]
    assert any(
        event["action"] == "override:edit"
        and event["item_id"] == image_id
        and event["before"] == "RECAPTURE"
        and event["after"] == "KEEP"
        for event in events
    )


def test_t02_rejects_review_for_image_outside_queue(tmp_path, capsys):
    queue = prepare_review(tmp_path)
    queue.loc[0, "item_id"] = "unknown_image"
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)

    assert run_poc(tmp_path) == 2
    assert "CSV review có ảnh ngoài hàng đợi hiện tại" in capsys.readouterr().err