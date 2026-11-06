# 8. Khái niệm xuyên suốt

## 8.1 Xác thực

Token ngẫu nhiên (`secrets.token_urlsafe(32)`), gửi `Authorization: Bearer`; DB lưu SHA-256 trong `auth_tokens` với hạn 30 ngày. EventSource dùng `?access_token=`. Frontend lưu token trong `localStorage`, mọi lời gọi qua `apiFetch`; `401` → xóa token, phát `shopping-ai:auth-expired`.

## 8.2 Phân quyền

`require_user` (mọi API riêng tư) và `require_admin` (thu thập hàng loạt, nhật ký guardrails). Quyền sở hữu kiểm tra ở route (`_own_session`, `_check_owner`) và ở repository (lọc `user_id`). Giao diện chỉ ẩn nút, không phải lớp bảo vệ.

## 8.3 Kiểm tra dữ liệu

Hai lớp: giao diện (báo lỗi tức thì) và backend (`validate_registration`, `validate_password`, Pydantic, kiểm tra nghiệp vụ như giá mong muốn). Backend là nguồn quyết định.

## 8.4 Xử lý lỗi

`HTTPException` với `detail` tiếng Việt; mã trạng thái theo [api/README.md](../../api/README.md#lỗi). Stream: sự kiện `error`. Agent: không ném lỗi ra ngoài khi LLM / sàn lỗi mà chuyển sang dự phòng và ghi `search_notes`.

## 8.5 Ghi log và nhật ký

`logging` theo module (`graph`, `ecom_search`, `price_watcher`…); không ghi khóa API, mật khẩu, token. Mỗi lần kiểm tra giá ghi một dòng vào bảng `price_checks` (kết quả accepted / triggered / pending / rejected / out_of_stock / unreadable, lý do, độ trễ; 100 dòng gần nhất mỗi yêu cầu). Chủ yêu cầu xem qua `/api/alerts/{id}/checks`, quản trị viên xem toàn hệ thống qua `/api/alerts/metrics`. Lịch sử hoạt động của người dùng là dữ liệu cá nhân (`user_data.activities`), không phải nhật ký kiểm toán.

## 8.6 Giao dịch CSDL

Mỗi phương thức repository một phiên, một commit. Ghi trạng thái hội thoại được nối tiếp theo phiên. Lưu lượt hội thoại chạy nền sau khi trả lời.

## 8.7 Nâng cấp lược đồ

`create_all` + `_add_missing_columns` khi khởi động; không dùng Alembic (xem ADR-009).

## 8.8 Độ tin cậy dữ liệu sản phẩm

- Nguồn của từng sản phẩm luôn được giữ (`platform`, `externalUrl`, trích dẫn trên giao diện).
- `updatedAt` của dữ liệu kho → ghi chú "cập nhật cách đây X giờ".
- Trạng thái thông số: `verified` / `mismatch` / `unknown`.

## 8.9 Thời gian

Lưu UTC không kèm múi giờ; frontend `parseServerDate` coi là UTC, hiển thị giờ địa phương `vi-VN`.

## 8.10 Bảo mật

bcrypt 12 vòng; chống dò email (cùng thông báo, cùng thời gian); khóa tạm 5 lần sai / 5 phút; bí mật chỉ trong `.env`; CORS giới hạn; nội dung LLM render thành phần tử React, không dùng `dangerouslySetInnerHTML`.

## 8.11 Thu thập dữ liệu có trách nhiệm

Cache nhiều tầng để giảm truy cập sàn; giới hạn đồng thời khi đọc trang chi tiết (6); thử lại có giới hạn; tắt nguồn có chống bot.

## 8.12 Giao diện sáng / tối

Tailwind 4 sinh utility dạng `var(--color-*)`; chế độ tối định nghĩa lại bảng màu dưới `.dark` nên mọi component đổi theo mà không cần `dark:`. Áp chế độ trong `index.html` trước khi React chạy để không nháy.
