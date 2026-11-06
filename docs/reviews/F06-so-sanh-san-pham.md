# F06 So sánh sản phẩm — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Đủ dùng, lời nhận xét còn mỏng
> Mã chính: [`backend/core/agents/comparison_agent.py`](../../backend/core/agents/comparison_agent.py), `POST /api/chat/compare` trong [`src/routes/chat.py`](../../backend/src/routes/chat.py), [`frontend/src/components/ComparisonTable.tsx`](../../frontend/src/components/ComparisonTable.tsx)

## Đã làm được

- Bảng so sánh trong khung chat: phù hợp, giá (đánh dấu thấp nhất), đánh giá, nơi bán, ưu / nhược, bảo hành, đổi trả.
- "Nhờ AI so sánh" từ mục Sản phẩm đã lưu (chọn ≥ 2) mà không cào lại.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | So sánh sản phẩm đã lưu chỉ dựng bảng + nhận xét theo luật, không có lời tư vấn LLM | `/api/chat/compare` | Người dùng không nhận được kết luận "nên chọn máy nào cho nhu cầu X" | Trung bình |
| 2 | Bảng chỉ có các trường chung, chưa có hàng thông số kỹ thuật theo ngành | `ComparisonTable.tsx` | So laptop không thấy CPU / RAM / GPU cạnh nhau | Trung bình |
| 3 | Giá trong mục Đã lưu là giá lúc lưu | dữ liệu `saved-products` | So sánh có thể dùng giá đã cũ (xem [F09](F09-san-pham-da-luu.md)) | Thấp |
| 4 | Không so được sản phẩm khác ngành | — | Không phải lỗi, nhưng giao diện không cảnh báo khi chọn lẫn ngành | Thấp |

## Đề xuất cải thiện

1. **Lời tư vấn khi so sánh đã lưu:** gọi advisor với danh sách sản phẩm + câu hỏi gốc của từng sản phẩm (đã lưu trong `Từ tìm kiếm`); trả lời ngắn "nên chọn … vì …".
2. **Hàng thông số theo ngành:** chọn 5–8 khóa thông số quan trọng theo danh mục (laptop: CPU, RAM, GPU, màn hình, pin, khối lượng; máy giặt: khối lượng giặt, inverter, kiểu cửa…) từ `specs` đã chuẩn hóa ([F05](F05-xep-hang-noi-long.md) #2); ô thiếu ghi "Chưa có dữ liệu".
3. **Cập nhật giá trước khi so sánh:** đọc giá hiện tại (dùng `fetch_current_price`) cho các sản phẩm đã lưu quá 24 giờ.
4. Cảnh báo khi chọn sản phẩm khác danh mục.

## Liên quan

[UC07](../03-use-cases.md), [F09](F09-san-pham-da-luu.md)
