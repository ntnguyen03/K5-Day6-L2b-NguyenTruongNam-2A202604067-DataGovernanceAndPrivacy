# Group Report — Day 06 Data Lab (Field-to-Release PoC)

> Điền đầy đủ, cụ thể, không viết chung chung. Mọi con số phải lấy từ file do script sinh ra
> (`reports/metrics_*.json`, `reports/table1_baseline_vs_poc.md`) — không gõ tay, không làm tròn mất đơn vị.
> 3–5 trang (hoặc README + report.md tương đương).

## 00 · Header

| Mục | Giá trị |
|---|---|
| Group ID | T065 |
| Challenge | T02 · Raw QC Triage |
| Thành viên và vai trò | Nguyễn Trường Nam (2A202604067) · Bài cá nhân. Phụ trách tích hợp, chạy thử, kiểm thử, duyệt ảnh và trình bày. |
| Git URL | [Repo bài tập](https://github.com/ntnguyen03/K5-Day6-L2b-NguyenTruongNam-2A202604067-DataGovernanceAndPrivacy) |
| Tag `demo-180m` (commit) |  |
| Tag `final-24h` (commit) |  |
| Deadline (giờ VN) | 12h00 15/11/2026 |

## 01 · Problem statement

- **Người chịu ảnh hưởng.** Người vận hành QC phải xem thêm ảnh nếu bảng xếp hạng ưu tiên nhầm. Nhóm dùng dữ liệu ở bước sau có thể nhận ảnh mất chi tiết nếu ảnh lỗi bị bỏ sót.
- **Điểm nghẽn.** Ngân sách chỉ đủ duyệt 20 ảnh. Mục tiêu là ưu tiên ảnh lỗi để người duyệt quyết định giữ hay chụp lại.
- **Đầu vào → đầu ra.** Ảnh JPEG và metadata → `ranked_review.csv`, hàng đợi top 20, contact sheet, audit log và quyết định.
- **Điều kiện quyết định.** HOLD khi hàng đợi còn ca chưa giải quyết. RECAPTURE (REWORK) khi đã duyệt đủ và còn ảnh cần chụp lại. KEEP (GO) khi đã duyệt đủ và giữ tất cả ảnh trong hàng đợi. Ngưỡng đề xuất theo từng ảnh được khai báo trong [metric contract](metric_contract.md).
- **Giả định nghiệp vụ.** Ảnh hơi mờ có thể còn đủ dùng cho nhận diện đối tượng nhưng có thể chưa đủ cho đọc biển số. Người phụ trách dữ liệu cần xác nhận tiêu chuẩn đủ dùng nếu triển khai thực tế.


## 02 · Data & provenance

| Split | N | Nguồn | License | Synthetic? |
|---|---:|---|---|---|
| dev | 56 | `fixtures/t02_raw_qc/images.csv` và ảnh JPEG | CC0-1.0 | Có |
| eval | 40 | Cùng fixture, giữ split theo cảnh gốc | CC0-1.0 | Có |

- Metadata gồm `image_id`, `path`, `camera_id`, `light` và `split`. Nhãn nội bộ dùng `none`, `blur`, `dark`, `glare`, `compression`. `is_defect=1` cho mọi loại lỗi, `0` cho `none`.
- Seed 42. Giữ nguyên split theo cảnh của fixture. Pipeline xuất điểm cho cả 96 ảnh, hàng đợi PoC và evaluator chỉ chọn từ eval.
- Kiểm SHA-256 bằng manifest, với `strict_provenance: true`. Trên Windows, các fixture bị đổi xuống dòng đã được khôi phục LF khi checksum sau khôi phục khớp manifest gốc. Kiểm tra môi trường bằng `python -m tools.preflight`.
- Thí nghiệm dùng ảnh tổng hợp. CSV nhãn nội bộ nằm trong `reports/t02_eval_labels_local.csv`.

## 03 · Research & design

- Chọn phương sai Laplacian làm baseline vì dễ chạy trên CPU và trực tiếp đo độ mạnh của cạnh. Thêm độ sáng theo bối cảnh và lóa theo ô để xét những lỗi có thể xuất hiện trên ảnh vẫn sắc nét. Các tài liệu dùng cho thiết kế nằm ở mục 11.
- Luồng xử lý: kiểm manifest → đọc ảnh và metadata → tính điểm → xếp top 20 eval → duyệt và áp override → ghi audit và quyết định → chấm điểm bằng evaluator riêng.
- Các đặc trưng dùng hàm xử lý ảnh trong repo. Các bước demo chạy offline, dùng CPU và không cần tải model.
- Lấy tín hiệu lớn nhất giúp giải thích từng điểm qua cột `reason`. Đổi lại, một tín hiệu tối mạnh có thể đẩy ảnh đêm sạch lên cao. Lưới cố định dễ cài nhưng có thể làm loãng đốm lóa nhỏ.


## 04 · Baseline vs PoC

- Baseline (mô tả, version/config, commit): ____
- PoC (mô tả, version/config, commit): ____
- Cùng budget / cùng heldout / cùng seed: xác nhận ____

**Bảng 1 · Baseline vs PoC & hard slices** — dán output của
`python -m src.compare reports/metrics_baseline.json reports/metrics_poc.json`:

Baseline: `baseline` (git b0ce8bf, seed 42) · PoC: `poc` (git b0ce8bf, seed 42)
- **Baseline Laplacian:** `src/baseline_t02.py` xếp hạng bằng `1 / (LaplacianVariance + 1e-6)`. Baseline ngẫu nhiên trong starter dùng để kiểm tra luồng ban đầu.
- **PoC:** `src/pipeline.py` lấy giá trị lớn nhất từ ba tín hiệu. Mờ dùng `35 / max(LaplacianVariance, 0.01)`. Tối dùng mức tham chiếu day/dusk/night là 45/32/18 chia cho `max(mean_gray, 1)`. Lóa dùng tỷ lệ pixel có luma trên 245 lớn nhất trong lưới 4 × 4, chia cho 0,40.
- Cả hai dùng 40 ảnh eval, cùng nhãn nội bộ, B = 20 và seed 42. SHA `b0ce8bf` do script ghi là HEAD lúc đo. Các thay đổi T02 lúc chạy nằm trong bản làm việc. Điền SHA triển khai ở mục 10 sau khi commit.

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Better | N |
|---|---|---|---|---|---|---|---|
| **Defect Recall@B** (GT defects in top-B / GT defects) | all | 0.8696 | 0.6522 | -0.2174 | -25.0% | higher | 40 |
| Precision@B (GT defects in top-B / B) | all | 1.0000 | 0.7500 | -0.2500 | -25.0% | higher | 40 |
| Defect-type accuracy (GT defects) (fraction) | all | n/a | 0.3913 | n/a | n/a | higher | 23 |
| False alarm in top-B (clean images in top-B / clean images) | light=day | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 20 |
| False alarm in top-B (clean images in top-B / clean images) | light=dusk | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 4 |
| False alarm in top-B (clean images in top-B / clean images) | light=night | 0.0000 | 0.8333 | 0.8333 | baseline=0 | lower | 16 |
| Runtime / 100 items (s) | all | 0.3026 | 0.3758 | | | lower | |

PoC giảm Recall@20 và Precision@20 trong lần đo này. Baseline tìm được 20/23 ảnh lỗi và PoC tìm được 15/23. Cả năm ảnh sạch chiếm chỗ trong top 20 của PoC đều là ảnh đêm.

## 05 · Evaluation protocol

- Ghép bằng `image_id`, lọc eval rồi xếp score giảm dần. TP là ảnh lỗi vào top 20, FP là ảnh sạch vào top 20, FN là ảnh lỗi nằm ngoài top 20. Recall = TP/(TP+FN). Precision = TP/20.
- Ngưỡng heuristic của PoC đề xuất RECAPTURE từ score ≥ 1. Điểm dùng để xếp hạng trước khi áp quyết định duyệt. Giữ cố định budget, split và công thức khi chấm. Thời điểm chốt protocol ghi trong [metric contract](metric_contract.md). Kiểm tra lại rằng giờ ghi trong đó là giờ thực tế trước khi nộp.
- CSV nội bộ có nhãn cho toàn bộ eval, kể cả ảnh ngoài top 20. Codex hỗ trợ gán nhãn từ quan sát ảnh sau lượt human review của người nộp. Điểm chính thức chờ nhãn giảng viên.
- Báo số đếm và mẫu số. Chưa tính CI. Các biến thể cùng cảnh có tương quan, vì vậy nếu bổ sung CI sẽ lấy mẫu theo cảnh gốc. Lệnh evaluate ở mục 08.

## 06 · Result slices

| Slice | N ảnh | Recall@20 trong slice · Baseline | Recall@20 trong slice · PoC | Ghi chú |
|---|---:|---:|---:|---|
| day | 20 | 0.9000 | 0.5000 | Không có ảnh sạch trong slice vào top 20 ở cả hai lần chạy |
| dusk | 4 | 1.0000 | 0.6667 | Slice nhỏ, chỉ có 3 ảnh lỗi |
| night | 16 | 0.8000 | 0.8000 | Ảnh sạch vào top 20: 0/6 với baseline, 5/6 với PoC |

Nguồn: `extra.slices` trong hai file `metrics_*.json`. Mỗi slice tính trên cùng top 20 toàn eval.

- **Ảnh đêm hữu ích bị ưu tiên nhầm.** `img_06_1` ở hạng 13, `reason=dark`, đề xuất KEEP. Biển báo, xe và người vẫn phân biệt được. Tối làm tăng điểm tương đối đủ để ảnh chiếm một suất trong hàng đợi, dù điểm dưới ngưỡng RECAPTURE.
- **Lóa cục bộ bị bỏ sót.** `img_05_3` có đốm trắng che một phần cụm xe bên trái và nằm ngoài top 20. Có thể vùng lóa chiếm tỷ lệ nhỏ trong ô lưới hoặc bị đường biên lưới chia ra. Đây là giả thuyết cần kiểm bằng cách xem tỷ lệ pixel bão hòa theo từng ô.
- **Chi phí chạy.** Từ Bảng 1, baseline 0.3026 s/100 ảnh (3.026 ms/ảnh), PoC 0.3758 s/100 ảnh (3.758 ms/ảnh). Đây là thời gian toàn pipeline ở hai lần chạy được ghi lại, bao gồm các bước khác nhau như contact sheet và review ở PoC.

## 07 · Human & decision

- `out/poc/review_queue.csv` và `contact_sheet.html` hiện 20 ảnh eval ưu tiên theo score. Nguyễn Trường Nam duyệt đủ 20, gồm 18 approve và 2 edit.
- `out/poc/review_queue_reviewed.csv` lưu quyết định thật. Hai ảnh `img_19_3` và `img_16_2` được đổi RECAPTURE → KEEP vì người duyệt vẫn nhìn thấy đối tượng. `out/poc/audit_log.jsonl` ghi reviewer, ID, lý do và giá trị trước/sau. Override giữ nguyên score dùng để tính metric.
- `out/poc/decision.json` ghi `resolved=20`, `recapture=7`, trạng thái RECAPTURE, canonical REWORK, mã `REVIEW_CONFIRMED_RECAPTURE`, owner Nguyễn Trường Nam.
- HOLD áp dụng khi có ca pending, skip hoặc escalate. Với hàng đợi đã giải quyết đủ, REWORK yêu cầu chụp lại các ảnh được người duyệt xác nhận.
Bằng chứng lượt duyệt: [CSV đã duyệt](review_evidence/review_queue_reviewed.csv), [audit log](review_evidence/audit_log.jsonl) và [quyết định cuối](review_evidence/decision.json).

## 08 · Reproduce & tests

Chạy trong CMD ở thư mục gốc repo. Sau khi cài `requirements.txt` vào `.venv`, các lệnh demo sau chạy offline.

```bat
.\.venv\Scripts\python.exe -m tools.preflight
.\.venv\Scripts\python.exe -m src.main --track t02 --pipeline src.baseline_t02 --output out/laplacian --run-name baseline --offline --seed 42
.\.venv\Scripts\python.exe -m src.main --track t02 --output out/poc --run-name poc --offline --seed 42
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --gt reports/t02_eval_labels_local.csv --pred out/laplacian/ranked_review.csv --run-name baseline --out reports/metrics_baseline.json
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --gt reports/t02_eval_labels_local.csv --pred out/poc/ranked_review.csv --run-name poc --out reports/metrics_poc.json
.\.venv\Scripts\python.exe -m src.compare reports/metrics_baseline.json reports/metrics_poc.json --out reports/table1_baseline_vs_poc.md
.\.venv\Scripts\python.exe -m pytest
```

Để tái hiện quyết định đã duyệt, đặt CSV review thật vào `out/poc/review_queue_reviewed.csv` trước khi chạy lại PoC.

- Kết quả pytest: **49 passed, 39 skipped in 6.24s**. Hai test T02 kiểm áp override và ghi audit đúng, cùng trường hợp CSV có ID ngoài hàng đợi trả exit code 2.
- Máy đo: Windows 11 build 26200, Python 3.12.10, CPU AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD. Git HEAD khi đo: `b0ce8bf`.

## 09 · Limitations & ethics

- Fixture sử dụng ảnh tổng hợp CC0-1.0. Nếu áp dụng ảnh thực tế có mặt người hay biển số, cần xác nhận quyền sử dụng, quyền truy cập và điều kiện lưu giữ với bên phụ trách. PoC là công cụ QC ảnh.
- Ảnh đêm có tỷ lệ báo nhầm cao trong hàng đợi. PoC chưa có tín hiệu nén JPEG riêng. Chưa thử 10 ảnh ngoài miền theo mốc +24h. Nhãn nội bộ chỉ phản ánh đánh giá thị giác trên fixture nhỏ.
- Khi lượng ảnh tăng 10×, chi phí tính đặc trưng có thể tăng theo lượng ảnh và ngân sách 20 lượt duyệt phải bao phủ tỷ lệ ảnh nhỏ hơn. Chưa đo ở quy mô này.
- Lần thử tiếp theo có thể dùng ngưỡng theo camera trên dev, cửa sổ lóa chồng lấp và tín hiệu block JPEG. Cần tập ảnh riêng để kiểm tra khả năng tổng quát.

## 10 · Team contribution

**Bảng 2 · Individual contribution evidence** (đối chiếu với `git shortlog -sne --all` và `reports/team_contributions.csv`)

| Học viên | Git author/email | Module / vai trò | Commit SHA / diff chứng minh | Trình bày? |
|---|---|---|---|---|
| Nguyễn Trường Nam (2A202604067) | [Điền Git author/email thực tế] | Cấu hình và tích hợp T02, trực tiếp duyệt ảnh, chạy đánh giá và kiểm thử | · `configs/lab.yaml`, `src/pipeline.py`, `src/baseline_t02.py`, `tests/test_t02_pipeline.py`, `reports/` | Không |

## 11 · References

| Tài liệu | Ngày xem | Ý nghĩa |
|---|---|---|
| [Đề T02](../docs/tracks/T02.md) | 14/11/2026 | Quy định budget, baseline, split và các ca lỗi cần phân tích. |
| [Hàm xử lý ảnh](../src/common/image_ops.py) | 14/11/2026 | Hiện thực grayscale và Laplacian variance dùng trong baseline. |
| [Evaluator theo track](../src/metrics/tracks.py) | 14/11/2026 | Định nghĩa Recall, Precision và false alarm theo slice, ghép theo ID ảnh. |

---

**Bảng 3 · Checklist chốt khi nộp**

- [ ] Link repo và tag cuối cùng trong README; input mẫu không chứa PII thật.
- [ ] Đúng 1 lệnh run, 1 lệnh evaluate, 1 lệnh tests; không cần download khi chạy.
- [ ] Có baseline/PoC metrics, ≥1 failure case, reviewer evidence, decision log.
- [ ] Có license/source provenance, data splits, seed, offline environment, GT/eval N.
- [ ] Mỗi thành viên có ≥1 commit thực chất và được nêu minh bạch trong bảng trên.
