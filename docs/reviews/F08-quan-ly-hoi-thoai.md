# F08 Quản lý hội thoại — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Dùng tốt một thiết bị, rủi ro khi nhiều thiết bị / nhiều worker
> Mã chính: [`frontend/src/components/SearchAssistantView.tsx`](../../frontend/src/components/SearchAssistantView.tsx), [`ConversationList.tsx`](../../frontend/src/components/ConversationList.tsx), [`backend/memory/session_manager.py`](../../backend/memory/session_manager.py), [`backend/database/repositories/chat_repo.py`](../../backend/database/repositories/chat_repo.py)

## Đã làm được

- Tạo / chuyển / xóa hội thoại; tên = câu hỏi đầu tiên; khóa chuyển / xóa khi đang trả lời.
- Hội thoại lưu theo tài khoản (`user_data.conversations`), trí nhớ phiên ở máy chủ (`chat_sessions`, `chat_messages`, `conversation_states`); xóa hội thoại xóa cả trí nhớ máy chủ; kiểm tra chủ sở hữu.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Toàn bộ hội thoại (kèm sản phẩm, bảng so sánh) lưu trong một khóa `user_data`, giới hạn 2 MB | `useSyncedState(userId, 'conversations')`, `MAX_USER_DATA_BYTES` | Hội thoại nhiều sản phẩm nhanh chạm giới hạn → lưu thất bại; mỗi thay đổi gửi lại cả khối | Trung bình |
| 2 | Tối đa 30 hội thoại, cái cũ bị cắt im lặng | `MAX_CONVERSATIONS` | Mất hội thoại cũ mà người dùng không biết | Trung bình |
| 3 | Ghi lượt chat xuống SQLite bằng task nền không chờ | `loop.create_task(...)` trong `session_manager.save_turn` / `set_state` | Tắt máy chủ đúng lúc → mất lượt cuối hoặc để lại khóa ghi (đã gặp "database is locked" trong test) | Trung bình |
| 4 | Bộ nhớ đệm phiên trong RAM | `SessionManager` | Chạy nhiều worker → mỗi worker một bản, trạng thái hỏi làm rõ có thể lệch | Thấp |
| 5 | Chưa đổi tên, tìm kiếm, ghim hội thoại | `ConversationList.tsx` | Khó tìm lại hội thoại cũ | Thấp |
| 6 | Hai nguồn sự thật: hội thoại ở `user_data` và tin nhắn ở `chat_messages` | — | Có thể lệch nhau (xóa ở một nơi, nơi kia còn) | Thấp |

## Đề xuất cải thiện

1. **Một nguồn sự thật:** dùng `chat_sessions` / `chat_messages` (đã có `user_id`) cho danh sách và nội dung hội thoại; thêm `GET /api/chat/sessions` (phân trang) và tải nội dung khi mở hội thoại; bỏ khóa `conversations` khỏi `user_data`. Giải quyết luôn #1, #2, #6.
2. **Ghi lượt chat có chờ:** `await` lưu trước khi gửi sự kiện `done`, hoặc giữ danh sách task và chờ hết trong `lifespan` khi tắt máy chủ.
3. **Thông báo khi vượt giới hạn** thay vì cắt im lặng (nếu chưa làm được #1).
4. Đổi tên và tìm kiếm hội thoại (cột `title` đã có trong `chat_sessions`).

## Liên quan

[UC10](../03-use-cases.md), [ADR-010, ADR-011](../architecture/arc42/09-architecture-decisions.md), [F01](F01-tai-khoan-xac-thuc.md) #5
