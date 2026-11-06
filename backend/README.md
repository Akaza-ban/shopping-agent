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
- Nghiệp vụ của từng bước nằm ở [core/flows/](core/flows/): hỏi làm rõ ngân sách, tìm kiếm (nới lỏng / upsell), câu hỏi gợi ý.

## 🗂️ Cấu trúc thư mục

```
src/            HTTP: main.py, lifespan.py, middleware/, dependencies/ (đăng nhập, workflow), schemas/ (dữ liệu vào/ra), routes/, errors.py
application/    use case của từng tính năng: auth, chat, compare, link, alerts, policies, products, feedback, crawler, user_data
core/           agent LangGraph: graph.py, flows/, agents/, prompts/, tools/, events.py (event SSE), i18n.py + locales/
services/       nghiệp vụ thuần: catalog (phân loại, xếp hạng, lọc), pricing (kiểm định giá), policy, rag, auth (băm mật khẩu, token)
integrations/   mọi lời gọi ra ngoài: llm/, platforms/ (từng sàn + đọc link), embedding.py, mail.py, policy_pages.py
jobs/           việc chạy nền: price_watcher.py, batch_crawler.py, warmup.py
database/       models/, repositories/, errors.py (SQLAlchemyError -> DatabaseError)
memory/         bộ nhớ hội thoại (RAM + SQLite)
shared/         dùng chung, không import tầng nào: config.py, exceptions.py, fallback.py, types.py, categories.py...
scripts/        lệnh chạy tay: catalog/, policy/, rag/, agent/
tests/          unit/ (logic, không cần CSDL / mạng), integration/ (API, CSDL tạm, LLM / sàn thật), fixtures/
```

Hướng import một chiều: `src, jobs, scripts → application → core → services → integrations, database → shared`.
Lỗi: tầng thấp đổi lỗi thư viện thành lỗi trong [shared/exceptions.py](shared/exceptions.py); [src/errors.py](src/errors.py) đổi lỗi nghiệp vụ thành HTTP 4xx.

| Muốn sửa... | Vào |
|---|---|
| Một API (tham số, mã lỗi trả về) | `src/routes/<tính năng>.py`, `src/schemas/<tính năng>.py` |
| Logic của một tính năng (VD điều kiện tạo theo dõi giá) | `application/<tính năng>.py` |
| Trợ lý hiểu sai câu hỏi | `core/agents/orchestrator.py`, `core/prompts/router_prompts.py` |
| Hỏi lại ngân sách không đúng lúc | `core/flows/clarification.py`, `core/constants.py` |
| Không tìm ra sản phẩm / nới lỏng tiêu chí | `core/flows/search_flow.py`, `core/tools/ecom_search.py` |
| Câu trả lời của trợ lý | `core/prompts/advisor_prompts.py`, `core/agents/advisor_context.py`; khi LLM lỗi: `advisor_fallback.py` |
| Câu chữ tiếng Việt / tiếng Anh của trợ lý | `core/locales/vi.json`, `en.json` |
| Đọc sai giá / thông số của một sàn | `integrations/platforms/<sàn>.py` (TGDĐ, ĐMX: `mwg.py`) |
| Loại giá bất thường | `services/pricing/guardrails.py` |
| Thứ tự xếp hạng sản phẩm | `services/catalog/ranker.py` |
| Nhà cung cấp LLM, model | `integrations/llm/client.py`, `.env` |
| Theo dõi giá định kỳ | `jobs/price_watcher.py` |

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
Cấu hình duy nhất nằm ở [shared/config.py](shared/config.py).

### 4. Khởi chạy máy chủ FastAPI
```bash
uvicorn src.main:app --reload --port 8000
```
- API Docs (Swagger UI): `http://localhost:8000/docs`
- Frontend `frontend` gọi tới `http://localhost:8000/api/...` (đặt `VITE_API_BASE_URL` nếu khác).

### 5. Chạy kiểm thử
```bash
pytest                       # toàn bộ tests/ (vài test integration gọi LLM thật nếu .env có khóa)
pytest tests/unit            # chỉ test logic, nhanh
RUN_LIVE_TESTS=1 pytest      # thêm các test cào sàn thật và đánh giá RAG trên kho thật
make lint                    # kiểm tra code bằng ruff (pip install ruff)
```
