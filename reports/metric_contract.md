# Metric contract (khai báo bắt buộc — chốt ở phút 30, trước khi chạy eval)

> Các metric chuẩn đã được cài trong `src/metrics/tracks.py`. File này là nơi nhóm **cam kết** cách dùng chúng.
> Không đổi testset, threshold hay trọng số sau khi đã thấy kết quả eval.

| Mục | Khai báo của nhóm |
|---|---|
| Track | T02 |
| Primary metric (tên đúng như evaluator in ra) |Defect Recall@B, với B = 20. Terminal hiển thị thêm `PRIMARY`|
| Tăng tốt hay giảm tốt? | higher |
| Đơn vị đánh giá (image / region / pair / release / batch / case …) | Một ảnh (image) |
| Công thức + numerator / denominator | Tử số: số ảnh có is_defect = 1 trong 20 ảnh điểm cao nhất trên eval. Mẫu số: tổng số ảnh có is_defect = 1 trong toàn bộ split eval|
| Cách ghép prediction ↔ GT (IoU? id? tolerance?) | Ghép bằng image_id. Xếp score giảm dần sau khi giới hạn vào các ID thuộc tập eval |
| Candidate pool cố định | fixtures/t02_raw_qc/images.csv. Pipeline dự đoán cho cả 96 ảnh. Pool dùng để tính metric chính thức là 40 ảnh có split=eval |
| Review budget B / K | B = 20 ảnh cho cả baseline Laplacian và PoC |
| Seed | 42 |
| Threshold policy (chọn trên dev như thế nào) | Chốt công thức và ngưỡng trước khi xem kết quả eval. Nếu cần điều chỉnh, chỉ xem ảnh hoặc nhãn tự gán trên 56 ảnh dev. Điểm nghi lỗi dùng để xếp hạng. Ngưỡng score >= 1 dùng để đề xuất RECAPTURE trong PoC theo code đã hướng dẫn |
| Eval split (không dùng để tune) | eval, gồm 40 ảnh. Giữ nguyên phân chia theo cảnh của fixture |
| Chỉ số lỗi xấu (miss / false alarm / false reject) | 	Miss: ảnh lỗi nằm ngoài top 20. False alarm: ảnh sạch nằm trong top 20. Báo thêm Precision@B = số ảnh lỗi trong top 20 / 20 |
| Slices sẽ báo cáo (≥2) | 	Theo light: day, dusk, night. Báo số mẫu, recall và false alarm theo từng nhóm. Ghi N/A nếu mẫu số bằng 0 |
| Cách báo độ bất định khi N nhỏ (Wilson CI / bootstrap) | Báo tử số/mẫu số và số ảnh mỗi slice. Với tập có nhãn và có ID cảnh, dùng bootstrap theo cảnh gốc vì các biến thể cùng cảnh có tương quan. Nếu chưa đủ dữ liệu để ước lượng, ghi rõ chưa tính CI |
| Ngày giờ chốt + người chốt | 22h-14/11/26 + Nguyễn Trường Nam |

Nếu baseline = 0 thì ghi rõ "baseline = 0" thay vì phần trăm cải thiện.
