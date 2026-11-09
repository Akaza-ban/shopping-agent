# Tài liệu API — Shopping AI

## Tổng quan

Backend FastAPI cung cấp REST (JSON) và Server-Sent Events. Đặc tả đầy đủ: [openapi.json](openapi.json) (OpenAPI 3.1, xuất từ `backend/src/main.py`). Khi máy chủ chạy có thể xem trực tiếp:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Xuất lại đặc tả sau khi đổi API:

```bash
cd backend
python -c "import json; from src.main import app; s=app.openapi(); s['paths']={p:v for p,v in s['paths'].items() if not p.startswith('/api/v1/')}; json.dump(s, open('../docs/api/openapi.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"
```

## Địa chỉ gốc

| Môi trường | URL |
|---|---|
| Cục bộ | `http://localhost:8000/api` |
| Bí danh | Mọi đường dẫn `/api/*` có bản tương đương `/api/v1/*` |

## Xác thực

- Đăng ký / đăng nhập trả `{ token, user }`. Gửi token ở mọi yêu cầu khác: `Authorization: Bearer <token>`.
- `GET /api/chat/stream` (dùng với `EventSource`, không gửi được header) nhận token qua `?access_token=<token>`.
- Token hết hạn sau 30 ngày; đăng xuất / đổi mật khẩu thu hồi ngay.
- Không có token hợp lệ → `401`; không đủ quyền → `403`.

## Danh sách endpoint

| Phương thức | Đường dẫn | Quyền | Chức năng |
|---|---|---|---|
| POST | `/auth/register` | công khai | Đăng ký |
| POST | `/auth/login` | công khai | Đăng nhập |
| POST | `/auth/logout` | người dùng | Thu hồi token hiện tại |
| GET / PATCH | `/auth/me` | người dùng | Hồ sơ / đổi tên hiển thị |
| POST | `/auth/change-password` | người dùng | Đổi mật khẩu (đăng xuất thiết bị khác) |
| GET / PUT | `/auth/me/data/{key}` | người dùng | Dữ liệu cá nhân (`conversations`, `saved-products`, `activities`, `search-history`) |
| POST | `/chat` | người dùng | Tư vấn, trả kết quả một lần |
| POST / GET | `/chat/stream` | người dùng | Tư vấn dạng SSE; `language: "vi" \| "en"` chọn ngôn ngữ trả lời (mặc định `vi`) |
| POST | `/chat/compare` | người dùng | So sánh danh sách sản phẩm |
| GET / DELETE | `/chat/history/{session_id}` | chủ hội thoại | Lịch sử / xóa hội thoại |
| GET | `/products/search` | người dùng | Tìm sản phẩm trực tiếp |
| GET | `/products/{id}` | người dùng | Chi tiết sản phẩm trong kho |
| GET | `/products/{id}/history` | người dùng | Lịch sử giá |
| POST | `/parse-link` | người dùng | Bóc tách link sản phẩm |
| GET / POST | `/alerts` | người dùng | Danh sách / tạo theo dõi giá (của mình) |
| DELETE | `/alerts/{id}` | chủ yêu cầu | Bỏ theo dõi |
| POST | `/alerts/check` | người dùng | Kiểm tra giá ngay (yêu cầu của mình) |
| GET | `/alerts/{id}/checks` | chủ yêu cầu | Nhật ký các lần kiểm tra giá của một yêu cầu (`?limit=`, tối đa 100) |
| GET | `/alerts/metrics` | quản trị viên | Nhật ký kiểm tra giá toàn hệ thống (`?user_id=`, `?limit=`) |
| GET | `/crawler/status` | người dùng | Tình trạng kho dữ liệu |
| POST | `/crawler/trigger` | quản trị viên | Thu thập hàng loạt |
| GET | `/health` (không có tiền tố `/api`) | công khai | Kiểm tra sống |

## Sự kiện SSE của `/chat/stream`

| `event` | `data` |
|---|---|
| `status` | `{stage, message}` — `routing`, `retrieval`, `relaxing`, `upsell`, `parsing_link`, `finding_deal`, `comparing`, `synthesizing` |
| `products` | `{count, items: ProductItemModel[]}` |
| `comparison` | `{summary, table: {columns, rows: [{label, values, best_index}]}}` |
| `clarification` | `{id, field, question, context_hint, options: [{id, label, value}], allow_custom_input, skip_value}`: LLM đặt câu hỏi, tối đa 3 câu cho một nhu cầu, mỗi lượt một câu; `skip_value` là câu gửi lại khi người dùng bấm "Bỏ qua" |
| `token` | `{content}` — từng đoạn lời tư vấn (Markdown) |
| `suggestions` | `string[]` |
| `done` | `{session_id, intent, recommended_product, clarification, relaxed_search, search_notes}` |
| `error` | `{error}` |

## Lỗi

Mọi lỗi trả `{"detail": "<thông báo tiếng Việt>"}`.

| Mã | Khi nào |
|---|---|
| 400 | Dữ liệu sai nghiệp vụ (giá mong muốn ≥ giá hiện tại, sai mật khẩu hiện tại) |
| 401 | Thiếu / sai / hết hạn token; sai email hoặc mật khẩu |
| 403 | Không đủ vai trò; truy cập hội thoại của người khác |
| 404 | Không tìm thấy (kể cả yêu cầu theo dõi giá của người khác) |
| 409 | Email đã đăng ký |
| 413 | Dữ liệu cá nhân > 2 MB |
| 422 | Dữ liệu không hợp lệ (định dạng, độ dài, mật khẩu yếu) |
| 429 | Khóa tạm sau 5 lần đăng nhập sai |

## Ví dụ cURL

```bash
# Đăng nhập
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"an@example.com","password":"matkhau123"}'

# Tư vấn dạng stream
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"session_id":"chat-001","message":"Laptop gaming dưới 25 triệu","platform":"all"}'

# Tạo theo dõi giá
curl -X POST http://localhost:8000/api/alerts \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"product":{"id":"tgdd-...","name":"...","platform":"tgdd","platformName":"Thế Giới Di Động","currentPrice":24790000,"externalUrl":"https://..."},"target_price":22310000}'
```

> Trên Windows Git Bash, tiếng Việt trong tham số `-d` có thể bị sai mã hóa; nên dùng tệp JSON (`-d @body.json`) hoặc client Python / Postman.

## Trạng thái triển khai

Tất cả endpoint trong bảng đã chạy và có test (xem [06-acceptance-criteria.md](../06-acceptance-criteria.md)). Xác thực được kiểm tra bằng dependency `require_user` / `require_admin` (`backend/src/auth.py`), không khai báo `securitySchemes` theo từng operation trong OpenAPI.
