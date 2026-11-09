# Cấu trúc thư mục — React và FastAPI

> Trạng thái: V1 — phản ánh mã nguồn hiện tại

## 1. Nguyên tắc chung

- Hai ứng dụng độc lập, giao tiếp qua HTTP/SSE: `backend/` (backend Python) và `frontend/` (frontend React).
- Backend phân tầng một chiều: `src/routes` → `core` (điều phối agent) → `services` / `memory` → `database`. Tầng dưới không import tầng trên.
- Mọi lời gọi backend của frontend đi qua `src/services/agentApi.ts` (gắn token, xử lý hết phiên).
- Cấu hình bí mật chỉ nằm trong `backend/.env` (không commit); mẫu ở `backend/.env.example`.

## 2. Bố cục kho mã

```text
20261/
├── backend/                      # Backend FastAPI + LangGraph
├── frontend/            # Frontend React 19 + Vite + Tailwind 4
├── docs/                   # Tài liệu dự án (thư mục này)
├── des.md                  # Mô tả đề tài ban đầu
└── Template ... .doc       # Mẫu báo cáo học phần
```

## 3. Backend (`backend/`)

```text
backend/
├── src/
│   ├── main.py             # Khởi tạo FastAPI, CORS, lifespan (init_db, làm ấm kho, theo dõi giá), đăng ký router
│   ├── config.py           # Settings (pydantic-settings) + get_chat_model (chuỗi dự phòng LLM)
│   ├── auth.py             # Dependency require_user / require_admin
│   └── routes/             # auth, chat, products, link_parser, alerts, crawler, policies
├── core/
│   ├── graph.py            # ShopAIAgentWorkflow: StateGraph LangGraph, hỏi làm rõ, tìm kiếm có nới lỏng
│   ├── state.py            # AgentState, UniversalSearchCriteria, ProductItemModel (Pydantic)
│   ├── agents/             # orchestrator, shopping_advisor, comparison_agent, link_parser_agent, deal_finder_agent
│   ├── tools/              # ecom_search (cache, RAG, cào song song qua services/catalog/platforms), spec_comparator, url_extractor, ...
│   └── prompts/            # router_prompts, advisor_prompts, parser_prompts
├── services/
│   ├── auth/               # service: băm mật khẩu, token, giới hạn đăng nhập sai
│   ├── catalog/            # Dữ liệu sản phẩm: categories (danh mục theo mã sàn), data_processor (làm sạch),
│   │   │                   # enricher (trang chi tiết, giá hiện tại), ranker, spec_fit (lọc + chấm theo thông số), batch_crawler, scraper
│   │   └── platforms/      # Các sàn (Strategy + Registry): base (giao diện chung), common (JSON-LD, từ khóa),
│   │                       # tiki, mwg (TGDĐ + ĐMX), fpt, cellphones, registry (danh sách sàn duy nhất)
│   ├── pricing/            # guardrails (giá bất thường), watcher (theo dõi giá định kỳ)
│   ├── policy/             # Chính sách đổi trả: service (tra cứu), fetcher (tải trang gốc),
│   │                       # extractor (LLM rút điều khoản), seed (dữ liệu nạp sẵn)
│   └── rag/                # RAG sản phẩm, xem docs/11-rag.md
├── memory/                 # session_manager (trí nhớ hội thoại RAM + SQLite)
├── database/
│   ├── connection.py       # Engine async, init_db, _add_missing_columns
│   ├── models/             # product, price_history, search_cache, chat_session, alert, user, policy
│   └── repositories/       # product_repo, chat_repo, alert_repo, user_repo, policy_repo
├── tests/                  # pytest + fixtures HTML thật của TGDĐ/ĐMX; conftest.py
├── scripts/                # Chạy trong backend/: python -m scripts.<nhóm>.<tên>
│   ├── catalog/            # crawl_hot, backfill_categories, clean_bad_prices
│   ├── rag/                # seed_catalog, reindex (nạp lại kho), eval (đo RAG)
│   ├── policy/             # fetch (tải trang chính sách), extract_terms (rút điều khoản để duyệt)
│   └── manual/             # Script thử tay: cào thử, luồng SSE, trí nhớ nhiều lượt
├── _legacy/                # Mã cũ không còn dùng (app/, config/), giữ để tham khảo
├── chroma_db/              # Dữ liệu ChromaDB: products_v2 (bge-m3), products_v1 (bản cũ) — sinh khi chạy
├── shopai.db               # SQLite (sinh khi chạy)
├── requirements.txt, pytest.ini, Makefile, README.md, .env.example
```

### Trách nhiệm theo tầng

| Tầng | Thư mục | Được phép phụ thuộc |
|---|---|---|
| API | `src/routes`, `src/auth.py` | `core`, `services`, `memory`, `database.repositories` |
| Điều phối agent | `core/graph.py`, `core/agents`, `core/tools`, `core/prompts` | `services`, `memory`, `database.repositories`, `src.config` |
| Dịch vụ | `services`, `memory` | `database.repositories`, `src.config`; `core.state` (kiểu dữ liệu) và `core.tools.ecom_search` (riêng `batch_crawler`) |
| Dữ liệu | `database` | `src.config` (URL CSDL) |

## 4. Frontend (`frontend/`)

```text
frontend/
├── index.html              # Áp chế độ sáng/tối trước khi React chạy
├── vite.config.ts
└── src/
    ├── main.tsx, App.tsx   # AuthProvider → AuthGate → ShoppingApp (dựng lại theo từng tài khoản)
    ├── index.css           # Token màu, chế độ tối (định nghĩa lại biến màu Tailwind)
    ├── types.ts            # Kiểu dữ liệu dùng chung
    ├── services/
    │   ├── agentApi.ts     # apiFetch, SSE client, chuyển đổi dữ liệu backend, API tài khoản / theo dõi giá / kho
    │   └── shoppingService.ts  # Danh mục sàn + dữ liệu tham khảo chính sách đổi trả
    ├── hooks/              # useAuth, usePreferences (giao diện, ngôn ngữ), useSyncedState, usePersistentState, usePriceAlerts
    ├── i18n/               # index.tsx (t, msg, I18nProvider), en.ts (bản dịch Việt -> Anh, mẫu câu backend)
    └── components/         # 20 component (màn hình, hộp thoại, bảng so sánh, biểu đồ giá, Markdown…)
scripts/check-i18n.mjs      # npm run i18n:check: chuỗi tiếng Việt chưa bọc t() / thiếu bản dịch
```

### Trách nhiệm

| Thành phần | Trách nhiệm |
|---|---|
| `components/*View.tsx` | Một màn hình; nhận dữ liệu và callback qua props |
| `components/*Modal.tsx` | Hộp thoại |
| `hooks/` | Trạng thái dùng chung: phiên đăng nhập, cài đặt người dùng, dữ liệu đồng bộ theo tài khoản, theo dõi giá |
| `i18n/` | Chuỗi giao diện viết bằng tiếng Việt và bọc `t('...')` (hằng số cấp module dùng `msg('...')` rồi dịch lúc hiển thị); câu tiếng Việt là khóa của bảng dịch `en.ts` |
| `services/agentApi.ts` | Ranh giới duy nhất với backend |

## 5. Quy ước đặt tên

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Module Python | `snake_case.py` | `product_ranker.py` |
| Lớp Python | `PascalCase` | `PriceWatcherService` |
| Bảng SQL | `snake_case` số nhiều | `price_alerts` |
| JSON API | `camelCase` cho dữ liệu sản phẩm / theo dõi giá; `snake_case` cho body yêu cầu | `currentPrice`, `target_price` |
| Component React | `PascalCase.tsx` | `TrackPriceModal.tsx` |
| Hook | `useXxx` | `useSyncedState` |
| Khóa localStorage | `shopping-ai.*`; theo tài khoản `shopping-ai.u.<userId>.*` | `shopping-ai.theme` |

## 6. Ánh xạ API → thư mục

| Nhóm API | Route | Logic chính |
|---|---|---|
| `/api/auth/*` | `src/routes/auth.py` | `services/auth/service.py`, `database/repositories/user_repo.py` |
| `/api/chat/*` | `src/routes/chat.py` | `core/graph.py`, `memory/session_manager.py`, `chat_repo.py` |
| `/api/products/*` | `src/routes/products.py` | `core/tools/ecom_search.py`, `product_repo.py` |
| `/api/parse-link` | `src/routes/link_parser.py` | `core/tools/url_extractor.py` |
| `/api/alerts/*` | `src/routes/alerts.py` | `services/pricing/watcher.py`, `alert_repo.py` |
| `/api/crawler/*` | `src/routes/crawler.py` | `services/catalog/batch_crawler.py` |

## 7. Cấu hình và bí mật

| Biến (`backend/.env`) | Ý nghĩa |
|---|---|
| `LLM_PROVIDER`, `DEEPSEEK_*`, `OPENROUTER_*`, `GROQ_*` | Nhà cung cấp LLM, khóa, model (chuỗi dự phòng) |
| `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_*_TIMEOUT_SECONDS` | Embedding RAG (mặc định `baai/bge-m3` qua OpenRouter) |
| `RAG_COLLECTION`, `RAG_MAX_AGE_DAYS` | Collection ChromaDB (`products_v2`), hạn dùng bản ghi (30 ngày) |
| `LANGCHAIN_*` | Tracing LangSmith (tùy chọn) |
| `DATABASE_URL` | Mặc định `sqlite+aiosqlite:///./shopai.db` |
| `CORS_ORIGINS` | Địa chỉ frontend được phép |
| `PRICE_WATCH_INTERVAL_MINUTES` | Chu kỳ kiểm tra giá (mặc định 360) |
| `ADMIN_EMAILS` | Email nhận vai trò quản trị khi đăng ký |

Frontend: `VITE_API_BASE_URL` (mặc định `http://localhost:8000`).
