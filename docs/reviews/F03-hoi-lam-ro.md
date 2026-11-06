# F03 Hỏi làm rõ — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Đúng nhưng hẹp (chỉ hỏi ngân sách)
> Mã chính: `_maybe_ask_clarification`, `_apply_pending_clarification`, `BUDGET_OPTIONS` trong [`backend/core/graph.py`](../../backend/core/graph.py); thẻ làm rõ trong [`SearchAssistantView.tsx`](../../frontend/src/components/SearchAssistantView.tsx)

## Đã làm được

- Hỏi ngân sách khi yêu cầu tìm mua chưa có giá, hãng hay model cụ thể; mức gợi ý theo ngành hàng + "Không giới hạn ngân sách".
- Mỗi ngành hàng hỏi một lần trong hội thoại; trạng thái chờ lưu SQLite (`conversation_states`), còn sau khi khởi động lại.
- Người dùng chọn nút hoặc gõ tự do; có "Bỏ qua".

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Chỉ hỏi ngân sách | `_maybe_ask_clarification` | Câu mơ hồ như "laptop tốt" vẫn thiếu mục đích dùng (học, gaming, đồ họa) → xếp hạng dựa vào ngân sách là chính | Trung bình |
| 2 | Mức ngân sách cố định trong mã | `BUDGET_OPTIONS`, `DEFAULT_BUDGET_OPTIONS` | Không theo giá thực tế của ngành hàng; ngành mới dùng mức mặc định (dưới 1 tr … trên 15 tr) | Thấp |
| 3 | Không biết người dùng đã nói ngân sách ở lượt trước theo cách gián tiếp | Router chỉ đọc câu hiện tại + trạng thái chờ | Có thể hỏi lại điều người dùng đã nói ("sinh viên, ít tiền") | Thấp |

## Đề xuất cải thiện

1. **Hỏi thêm mục đích sử dụng** cho các ngành có nhu cầu khác nhau rõ (laptop, điện thoại, máy giặt theo số người…): thêm câu hỏi thứ hai có lựa chọn; ánh xạ lựa chọn → thuộc tính bắt buộc / ưu tiên trong `UniversalSearchCriteria`. Giới hạn tối đa 2 câu hỏi mỗi hội thoại.
2. **Mức ngân sách từ dữ liệu:** tính phân vị 25/50/75 giá của ngành hàng trong bảng `products`, làm tròn thành các mức; dùng mức cố định khi kho ít dữ liệu.
3. **Suy ngân sách từ ngữ cảnh** ("sinh viên", "giá rẻ", "cao cấp") bằng router, chỉ hỏi khi thật sự không suy được.
4. Kiểm chứng: thêm ca vào bộ đánh giá câu trả lời ([F02](F02-tu-van-mua-sam.md) #1) — đếm số lượt hỏi thừa.

## Liên quan

[UC06](../03-use-cases.md), [BR về hỏi làm rõ](../requirements/business-rules.md)
