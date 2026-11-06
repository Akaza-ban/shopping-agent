# Mô hình dữ liệu (SQLite + ChromaDB)

> Trạng thái: V1 — model SQLAlchemy trong `backend/database/models/`, tạo tự động khi khởi động (`init_db`)

Sơ đồ quan hệ: [DATABASE.md](DATABASE.md).

## Các bảng

| Bảng | Mục đích | Khóa chính | Ghi chú |
|---|---|---|---|
| `users` | Tài khoản | `id` (`user-<hex>`) | `email` duy nhất, lưu chữ thường; `role` = `user` \| `admin` |
| `auth_tokens` | Phiên đăng nhập | `token_hash` (SHA-256) | `expires_at` = tạo + 30 ngày; xóa khi đăng xuất |
| `user_data` | Dữ liệu giao diện theo tài khoản | `id`; duy nhất (`user_id`, `key`) | `key` ∈ `conversations`, `saved-products`, `activities`, `search-history`; ≤ 2 MB |
| `products` | Kho sản phẩm đã thu thập | `id` (`tgdd-…`, `dmx-…`, `tiki-…`) | Giá, đánh giá, thông số (JSON), bảo hành, link |
| `price_history` | Mốc giá | `id` | FK `product_id` → `products` (cascade); chỉ ghi khi giá đổi ≥ 1 đ |
| `search_cache` | Cache từ khóa → danh sách sản phẩm | `id` | `product_ids` JSON; `expires_at` = tạo + 2 giờ |
| `chat_sessions` | Hội thoại | `id` (do giao diện sinh) | `user_id` = chủ sở hữu (NULL với hội thoại tạo trước khi có tài khoản) |
| `chat_messages` | Tin nhắn | `id` | `session_id`; tin của trợ lý kèm `products_json`, `criteria_json` |
| `conversation_states` | Trạng thái giữa các lượt | `session_id` | `state_json` = `{pending_clarification, clarified_categories}` |
| `price_alerts` | Yêu cầu theo dõi giá | `id` (`alert-<ms>`) | `user_id`, `product_id`, giá mong muốn / ban đầu / gần nhất / thấp nhất, `status`, `pending_price`, `in_stock` |
| `price_checks` | Nhật ký kiểm tra giá | `id` (tự tăng) | `alert_id`, `user_id`, `price`, `in_stock`, `outcome` (accepted / triggered / pending / rejected / out_of_stock / unreadable), `note`, `latency_ms`, `checked_at`; giữ 100 dòng mỗi yêu cầu |

Ngoài SQLite, **ChromaDB** (`backend/chroma_db/`, collection `products_v2`, khoảng cách cosine) lưu vector bge-m3 1024 chiều của tài liệu mô tả sản phẩm (tên, ngành hàng, thông số, bảo hành — không có giá). Metadata: `product_id`, `name`, `category` (đã chuẩn hóa), `platform`, `current_price`, `original_price`, `discount_percent`, `rating`, `external_url`, `updated_at` (epoch), `raw_json`. Collection cũ `products_v1` (embedding tiếng Anh mặc định) còn trên đĩa để so sánh. Chi tiết: [11-rag.md](11-rag.md).

## Chi tiết cột chính

### `users`

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | VARCHAR | PK |
| `email` | VARCHAR | NOT NULL, UNIQUE, chỉ mục |
| `display_name` | VARCHAR | NOT NULL, 2–50 ký tự (kiểm tra ở API) |
| `password_hash` | VARCHAR | NOT NULL, bcrypt (12 vòng) |
| `role` | VARCHAR | NOT NULL, mặc định `user` |
| `created_at`, `last_login_at` | DATETIME | UTC |

### `price_alerts`

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | VARCHAR | PK |
| `user_id` | VARCHAR | chỉ mục; mọi truy vấn API lọc theo người dùng hiện tại |
| `product_id` | VARCHAR | chỉ mục; tham chiếu mềm `products.id` |
| `product_name`, `product_url`, `image`, `platform`, `platform_name` | VARCHAR | thông tin hiển thị |
| `target_price` | FLOAT | NOT NULL, > 0 và < giá hiện tại (kiểm tra ở API) |
| `initial_price`, `last_price`, `lowest_price` | FLOAT | |
| `status` | VARCHAR | `watching` \| `triggered`, chỉ mục |
| `last_checked_at`, `triggered_at` | DATETIME | UTC |
| `last_note` | TEXT | kết quả lần kiểm tra gần nhất |
| `pending_price`, `pending_at` | FLOAT, DATETIME | giá bất thường chờ lần đọc sau xác nhận (BR-011) |
| `in_stock` | BOOLEAN | còn hàng ở lần đọc gần nhất; NULL = sàn không ghi |
| `user_email` | VARCHAR | NOT NULL, mặc định rỗng; dự phòng cho thông báo email |

### `products` và `price_history`

Xem cột đầy đủ trong `backend/database/models/product.py`, `price_history.py`. `upsert_products` thêm sản phẩm mới kèm mốc giá đầu tiên; với sản phẩm đã có, chỉ thêm mốc giá khi giá thay đổi.

## Nâng cấp lược đồ

Không dùng Alembic. Khi khởi động, `init_db` chạy `create_all` (tạo bảng mới) rồi `_add_missing_columns` (thêm cột mới vào bảng đã có bằng `ALTER TABLE … ADD COLUMN`). Chỉ áp dụng cho cột cho phép NULL hoặc có mặc định. Đổi kiểu / xóa cột cần di chuyển dữ liệu thủ công.

## Ranh giới giao dịch

- Mỗi phương thức repository mở một phiên SQLAlchemy và commit một lần.
- Ghi trạng thái hội thoại (`update_conversation_state`) được xếp hàng tuần tự theo phiên để bản cũ không ghi đè bản mới.
- Lưu lượt hội thoại chạy ngầm (`create_task`) sau khi trả lời xong, không chặn stream.

## Thời gian và tiền tệ

- Mọi thời điểm lưu theo UTC (`datetime.utcnow()`, không kèm múi giờ). Giao diện coi chuỗi không có múi giờ là UTC (`parseServerDate`) rồi hiển thị theo giờ địa phương.
- Giá lưu bằng VND, kiểu FLOAT, không quy đổi tiền tệ.

## Dữ liệu nhạy cảm

- Không lưu mật khẩu gốc, không lưu token gốc.
- Khóa API của nhà cung cấp LLM chỉ nằm trong `backend/.env`.
- `user_data` chỉ đọc / ghi được bởi chính chủ tài khoản.

## Ánh xạ dữ liệu frontend

| Kiểu frontend (`types.ts`) | Nguồn |
|---|---|
| `ProductItem` | `ProductItemModel` của backend qua `toProductItem` (giữ `raw` khi cần gửi lại) |
| `ChatConversation` | `user_data[conversations]` (sản phẩm lưu dạng gọn, không có `raw`) |
| `SavedProduct`, `ActivityItem`, `SearchRecord` | `user_data[saved-products / activities / search-history]` |
| `PriceAlert` | `price_alerts` qua `alert_to_dict` |
| `PricePoint` | `price_history` |
