# ShopAI Multi-Agent Backend System

Backend AI Agent cho ứng dụng trợ lý mua sắm **ShopAI** (frontend nằm ở thư mục `../frontend`).

## 🌟 Tính Năng Của Hệ Thống Agent

1. **Orchestrator Agent**: Phân tích câu hỏi người dùng, trích xuất tiêu chí và quyết định nhánh xử lý (Tìm kiếm, So sánh, Săn deal, Bóc tách link hay Tư vấn).
2. **Shopping Advisor Agent**: Đàm thoại, tư vấn lựa chọn sản phẩm dựa trên nhu cầu sử dụng và ngân sách, chỉ dùng dữ liệu đã thu thập.
3. **Comparison Agent**: Bảng so sánh giá, cấu hình, bảo hành, đổi trả giữa các sản phẩm (Tiki, Thế Giới Di Động, Điện Máy Xanh).
4. **Link Parser Agent**: Đọc URL sản phẩm người dùng dán vào, trích xuất thông số, giá và hình ảnh.
5. **Deal Finder Agent**: Đưa sản phẩm đang giảm giá sâu nhất lên đầu và ghi chú mức tiết kiệm thực tế.

## 🧭 Kiến trúc LangGraph

Toàn bộ luồng xử lý là một `StateGraph` trong [core/graph.py](core/graph.py):

```
START → load_session → route → clarify ─┬─ ask (hỏi ngân sách) ───────────────┐
                                        ├─ parse_link ─────────────► respond → finalize → END
                                        ├─ search ──► compare ─────► respond
                                        ├─ deal ────► compare ─────► respond
                                        └─ (tư vấn chung) ─────────► respond
```

- `POST /api/chat` chạy `graph.ainvoke`, `POST /api/chat/stream` chạy `graph.astream(stream_mode="custom")`, cùng một graph.
- Mỗi node phát sự kiện SSE qua `get_stream_writer()`: `status`, `products`, `comparison`, `clarification`, `token`, `suggestions`, `done`.
- Trạng thái giữa các lượt (câu hỏi làm rõ đang chờ trả lời) lưu ở bảng `conversation_states` trong SQLite, nên vẫn còn sau khi khởi động lại server.
- `POST /api/chat/compare` so sánh danh sách sản phẩm do giao diện gửi lên (VD: mục "Đã lưu") mà không cào lại.

## 🔐 Tài khoản & phân quyền

- `POST /api/auth/register`, `POST /api/auth/login` trả về token phiên (Bearer). Các API khác đều yêu cầu đăng nhập; `GET /api/chat/stream` (EventSource) nhận token qua `?access_token=`.
- Mật khẩu băm bằng bcrypt; DB chỉ lưu SHA-256 của token nên đăng xuất / đổi mật khẩu thu hồi được phiên ngay. Sai mật khẩu 5 lần liên tiếp bị khóa 5 phút.
- Hội thoại (`chat_sessions.user_id`) và theo dõi giá (`price_alerts.user_id`) thuộc về người tạo; người khác truy cập nhận 403 / 404.
- Dữ liệu giao diện (hội thoại, sản phẩm đã lưu, lịch sử) đồng bộ qua `GET/PUT /api/auth/me/data/{key}` để dùng trên nhiều thiết bị.
- Quản trị viên: email liệt kê trong `ADMIN_EMAILS` (`.env`) nhận vai trò `admin` khi đăng ký; chỉ quản trị viên được kích hoạt thu thập dữ liệu và xem nhật ký guardrails.

## 🔎 RAG sản phẩm

- Embedding đa ngôn ngữ `baai/bge-m3` qua OpenRouter (dùng lại `OPENROUTER_API_KEY`), lưu ChromaDB collection `products_v2`.
- Truy xuất lai vector + BM25 hợp nhất RRF; lọc danh mục đã chuẩn hóa, giá, sàn, độ mới (`RAG_MAX_AGE_DAYS`). Embedding API lỗi → chỉ tìm từ khóa → không đạt thì cào trực tiếp.
- `python -m scripts.rag.reindex` nạp lại kho (cần khi đổi `EMBEDDING_MODEL` / `RAG_COLLECTION`); `python -m scripts.rag.eval` đo recall@5 / MRR trên 51 truy vấn có nhãn. Chi tiết: [`docs/11-rag.md`](../docs/11-rag.md).

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### 1. Tạo môi trường ảo Python
```bash
# Tại thư mục backend:
python -m venv .venv

# Kích hoạt trên Windows:
.\.venv\Scripts\activate
# Hoặc trên Linux/macOS:
source .venv/bin/activate
```

### 2. Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` từ `.env.example`:
```bash
copy .env.example .env
```
Điền ít nhất một khóa LLM: `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY` hoặc `GROQ_API_KEY`. Hệ thống tự chuyển sang nhà cung cấp kế tiếp khi một bên lỗi.
Cấu hình duy nhất nằm ở [src/config.py](src/config.py).

### 4. Khởi chạy máy chủ FastAPI
```bash
uvicorn src.main:app --reload --port 8000
```
- API Docs (Swagger UI): `http://localhost:8000/docs`
- Frontend `frontend` gọi tới `http://localhost:8000/api/...` (đặt `VITE_API_BASE_URL` nếu khác).

### 5. Chạy kiểm thử
```bash
pytest                       # thư mục tests/ (vài test gọi LLM thật nếu .env có khóa)
RUN_LIVE_TESTS=1 pytest      # thêm các test cào sàn thật và đánh giá RAG trên kho thật
```
