# 5. Góc nhìn khối xây dựng

## 5.1 Mức 1 — Shopping AI

Hệ thống gồm hai container triển khai riêng (frontend, backend) và hai kho dữ liệu nhúng trong backend (SQLite, ChromaDB). Xem [C4 mức 2](../c4/02-container.md).

## 5.2 Mức 2 — Container

| Container | Công nghệ | Trách nhiệm |
|---|---|---|
| Web App | React 19, Vite, Tailwind 4 | Giao diện, phiên đăng nhập phía client, đọc SSE, đồng bộ dữ liệu cá nhân |
| API & Agent Backend | FastAPI, LangGraph, LangChain | Xác thực, điều phối agent, thu thập, xếp hạng, theo dõi giá |
| CSDL quan hệ | SQLite (aiosqlite) | Tài khoản, phiên, sản phẩm, lịch sử giá, hội thoại, theo dõi giá, dữ liệu cá nhân |
| CSDL vector | ChromaDB | Tìm sản phẩm theo ngữ nghĩa |

## 5.3 Mức 3 — Thành phần backend

| Thành phần | Mã | Trách nhiệm |
|---|---|---|
| Auth | `src/routes/auth.py`, `src/auth.py`, `services/auth/service.py`, `user_repo.py` | Đăng ký, đăng nhập, phiên, quyền, dữ liệu cá nhân |
| Chat API | `src/routes/chat.py` | Kiểm tra quyền sở hữu hội thoại, gọi workflow, stream SSE |
| Agent Workflow | `core/graph.py` | Đồ thị LangGraph, hỏi làm rõ, tìm kiếm có nới lỏng / tìm thêm |
| Orchestrator | `core/agents/orchestrator.py` | Phân loại ý định, trích tiêu chí (LLM + dự phòng từ khóa) |
| EcomSearch | `core/tools/ecom_search.py` | Cache-first, cào TGDĐ/ĐMX/Tiki, lọc, hoàn thiện kết quả |
| Enricher | `services/catalog/enricher.py` | Trang chi tiết: thông số, bảo hành, đổi trả, giá hiện tại |
| Ranker | `services/catalog/ranker.py` | Đối chiếu thông số, chấm điểm, lý do |
| Spec Fit | `services/catalog/spec_fit.py` | Một lần gọi LLM vừa loại phụ kiện / hàng không liên quan, vừa chấm mức hợp nhu cầu từ thông số trang chi tiết |
| RAG | `services/rag/` (`service.py` + embedding, BM25, bộ lọc, chấm điểm) | ChromaDB, embedding API |
| Comparison | `core/agents/comparison_agent.py`, `core/tools/spec_comparator.py` | Bảng so sánh |
| Advisor | `core/agents/shopping_advisor.py`, `core/prompts/advisor_prompts.py` | Ngữ cảnh chuẩn hóa, lời tư vấn stream, câu trả lời dự phòng |
| DealFinder / LinkParser | `core/agents/deal_finder_agent.py`, `link_parser_agent.py` | Săn deal, bóc tách link |
| Session Memory | `memory/session_manager.py`, `chat_repo.py` | Trí nhớ hội thoại hai tầng, trạng thái giữa các lượt |
| Price Watcher | `services/pricing/watcher.py`, `services/pricing/guardrails.py`, `alert_repo.py` | Theo dõi giá, kiểm định giá |
| Batch Crawler | `services/catalog/batch_crawler.py` | Làm ấm / thu thập hàng loạt |
| Product Repository | `product_repo.py` | Sản phẩm, lịch sử giá, cache tìm kiếm |

## 5.4 Ánh xạ giao diện → thành phần

| Màn hình | Thành phần |
|---|---|
| SCR-01, DLG-04 | Auth |
| SCR-03 | Chat API → Agent Workflow (Orchestrator, EcomSearch, Enricher, Ranker, Comparison, Advisor, DealFinder, LinkParser) |
| SCR-05 | Auth (user data), Comparison |
| SCR-06, DLG-01 | Price Watcher, Product Repository |
| DLG-02 | Batch Crawler |

## 5.5 Quy tắc phụ thuộc

- Route không truy cập SQLAlchemy trực tiếp; đi qua repository.
- Agent / tool không gọi route.
- `services` / `memory` không import đồ thị hay agent. Ngoại lệ có chủ đích: `memory/session_manager` dùng kiểu dữ liệu `core.state`; `services/batch_crawler` dùng công cụ `core.tools.ecom_search` để thu thập hàng loạt.
- Frontend chỉ gọi backend qua `agentApi.ts`.

## 5.6 Mức 4 — Hai luồng cốt lõi

Xem [C4 mức 4](../c4/04-code.md) và [UML lớp](../uml/01-class-diagrams.md): (1) tư vấn mua sắm qua `ShopAIAgentWorkflow`; (2) theo dõi giá qua `PriceWatcherService`.
