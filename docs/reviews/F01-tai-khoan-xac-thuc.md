# F01 Tài khoản & xác thực — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Chạy tốt, cần gia cố khi triển khai thật
> Mã chính: [`backend/services/auth/service.py`](../../backend/services/auth/service.py), [`backend/src/auth.py`](../../backend/src/auth.py), [`backend/src/routes/auth.py`](../../backend/src/routes/auth.py), [`frontend/src/hooks/useAuth.tsx`](../../frontend/src/hooks/useAuth.tsx), [`frontend/src/hooks/useSyncedState.ts`](../../frontend/src/hooks/useSyncedState.ts)

## Đã làm được

- Đăng ký / đăng nhập / đăng xuất; mật khẩu băm bcrypt (12 vòng); kiểm tra email, mật khẩu ≥ 8 ký tự có chữ và số.
- Token ngẫu nhiên, CSDL chỉ lưu SHA-256, hạn 30 ngày; đăng xuất / đổi mật khẩu thu hồi được ngay.
- Khóa 5 phút sau 5 lần sai; băm giả để thời gian phản hồi như nhau (chống dò email).
- Phân quyền `user` / `admin` theo `ADMIN_EMAILS`; kiểm tra quyền sở hữu ở route và repository.
- Dữ liệu giao diện đồng bộ theo tài khoản (`user_data`, giới hạn 2 MB mỗi khóa).
- Test: `tests/test_auth.py` (10 test).

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Bộ đếm đăng nhập sai nằm trong RAM | `LoginThrottle._failures` trong `services/auth/service.py` | Khởi động lại là mất; chạy nhiều worker thì mỗi worker đếm riêng → kẻ dò mật khẩu được nhân số lần thử | Trung bình |
| 2 | Không giới hạn tần suất gọi API tư vấn theo người dùng | Mọi route `/api/chat*` | Một tài khoản có thể gửi liên tục, mỗi lượt tốn 2–4 lần gọi LLM + embedding → chi phí không kiểm soát | Cao |
| 3 | `GET /api/chat/stream` nhận token qua `?access_token=` | `_token_from_request` trong `src/auth.py` | Token có thể nằm trong log máy chủ / proxy. Giao diện hiện dùng `POST` + header nên chưa bị, nhưng đường này vẫn mở | Thấp |
| 4 | Token hết hạn không bao giờ bị xóa | Bảng `auth_tokens` | Bảng phình dần | Thấp |
| 5 | Dữ liệu cá nhân ghi đè nguyên khối, bản sau thắng | `PUT /api/auth/me/data/{key}`, `useSyncedState` (debounce 800 ms) | Mở 2 thiết bị cùng lúc → thao tác trên thiết bị này có thể xóa thao tác của thiết bị kia; đăng xuất trong 0,8 s mất thay đổi cuối | Trung bình |
| 6 | Chưa có quên mật khẩu, xác thực email, quản trị người dùng | — | Người dùng quên mật khẩu không tự khôi phục được; vai trò chỉ gán lúc đăng ký | Trung bình |

## Đề xuất cải thiện

1. **Giới hạn tần suất (ưu tiên cao):** đếm số lượt chat theo `user_id` trong cửa sổ trượt (VD 30 lượt / 10 phút) lưu SQLite; quá hạn → `429` kèm thời gian chờ. Kiểm chứng: test gửi 31 lượt nhận `429`.
2. **Bộ đếm đăng nhập sai lưu bền:** chuyển sang bảng `login_attempts (email, count, since)`; dọn khi đăng nhập đúng.
3. **Đồng bộ dữ liệu cá nhân có phiên bản:** thêm cột `version` cho `user_data`; `PUT` gửi kèm `If-Match`, lệch thì `409` và giao diện gộp lại (với danh sách: gộp theo `id`). Gửi bản cuối bằng `navigator.sendBeacon` khi đăng xuất / đóng tab.
4. **Dọn token hết hạn** trong vòng nền của Price Watcher (1 lần/ngày).
5. **Bỏ `?access_token=`** nếu không còn dùng EventSource, hoặc đổi sang token ngắn hạn dùng một lần cho SSE.
6. Quên mật khẩu qua email (cần dịch vụ gửi thư — dùng chung với thông báo đạt giá ở F10).

## Liên quan

[BR-001 … BR-003](../requirements/business-rules.md), [arc42 §8](../architecture/arc42/08-crosscutting-concepts.md), [ADR-008](../architecture/arc42/09-architecture-decisions.md)
