# F05 Xếp hạng & nới lỏng tiêu chí — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Logic rõ ràng, chưa được đo
> Mã chính: [`backend/services/catalog/ranker.py`](../../backend/services/catalog/ranker.py), `_annotate_attribute_match` trong [`ecom_search.py`](../../backend/core/tools/ecom_search.py), nới lỏng trong [`graph.py`](../../backend/core/graph.py)

## Đã làm được

- Điểm 0–100 có lý do: khớp thông số 35, ngân sách 20, chất lượng 25, giảm giá 10, sở thích 10 (`BASE_WEIGHTS`); đổi trọng số theo ưu tiên (`PRIORITY_WEIGHTS`, VD "rẻ nhất").
- Đánh giá có trọng số Bayes; sản phẩm sai thông số bắt buộc tối đa 55 điểm, nhãn "Không đúng cấu hình yêu cầu".
- Nới lỏng có thứ tự: bỏ thông số → +20% ngân sách → bỏ hãng; tìm thêm tới +20% ngân sách khi không có máy đúng cấu hình; ghi chú trung thực.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Trọng số đặt tay, chưa có dữ liệu kiểm chứng | `BASE_WEIGHTS`, `PRIORITY_WEIGHTS` | Không biết thứ hạng có hợp ý người dùng không | Trung bình |
| 2 | Khớp thông số dựa vào chuỗi trong tên / thông số đã đọc | `_annotate_attribute_match` | Thông số ghi khác cách (VD "RTX4050" / "GeForce RTX 4050 6GB") hoặc thiếu trang chi tiết → "Chưa xác minh" | Trung bình |
| 3 | Điểm "giảm giá" tin giá gốc của sàn | phần `deal` trong ranker | Giá gạch bị đẩy cao làm sản phẩm trông như đang giảm sâu | Thấp |
| 4 | Không có tín hiệu từ hành vi người dùng | — | Lưu / theo dõi giá / mở trang sàn không ảnh hưởng xếp hạng sau này | Thấp |

## Đề xuất cải thiện

1. **Bộ đánh giá xếp hạng:** 20–30 tình huống (câu hỏi + danh sách sản phẩm cố định + thứ tự mong muốn do người làm nhãn); đo NDCG@3; dùng để chỉnh trọng số thay vì đoán.
2. **Chuẩn hóa thông số trước khi so:** từ điển đồng nghĩa (GPU, CPU, RAM, dung tích, khối lượng) + regex tách số và đơn vị; dùng chung cho xếp hạng và bảng so sánh.
3. **Giảm giá theo lịch sử:** so giá hiện tại với giá thấp nhất / trung vị trong `price_history` khi có ≥ 3 mốc, thay vì chỉ tin giá gốc (xem [F07](F07-san-deal-tham-dinh-link.md)).
4. Ghi nhận tín hiệu (lưu, theo dõi giá, bấm "Xem tại sàn") vào nhật ký; sau này dùng làm dữ liệu chỉnh trọng số.

## Liên quan

[BR về xếp hạng và nới lỏng](../requirements/business-rules.md), [UC05](../03-use-cases.md)
