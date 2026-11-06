# C3 — Thành phần backend

```mermaid
flowchart TB
    web["Web App"]

    subgraph api["API & Agent Backend"]
        direction TB
        subgraph routes["Tầng API (src/routes)"]
            authR["Auth API"]
            chatR["Chat API"]
            alertR["Alerts API"]
            prodR["Products / Parse-link API"]
            crawlR["Crawler API"]
        end
        guard["Auth dependency<br/>require_user / require_admin"]

        subgraph agent["Điều phối agent (core)"]
            wf["Agent Workflow<br/>(LangGraph)"]
            orch["Orchestrator"]
            adv["Advisor"]
            cmp["Comparison"]
            deal["DealFinder"]
            link["LinkParser"]
            search["EcomSearch tool"]
        end

        subgraph svc["Dịch vụ"]
            enr["Enricher"]
            rank["Ranker"]
            sem["Semantic Filter"]
            rag["RAG"]
            watch["Price Watcher + Guardrails"]
            batch["Batch Crawler"]
            mem["Session Memory"]
            authS["Auth service"]
        end

        subgraph data["Tầng dữ liệu (repositories)"]
            userRepo["UserRepository"]
            chatRepo["ChatRepository"]
            prodRepo["ProductRepository"]
            alertRepo["AlertRepository"]
        end
    end

    db[("SQLite")]
    vec[("ChromaDB")]
    llm["LLM"]
    shops["Sàn TMĐT"]

    web --> routes
    routes --> guard --> userRepo
    authR --> authS
    authR --> userRepo
    chatR --> wf
    chatR --> chatRepo
    alertR --> watch
    alertR --> alertRepo
    prodR --> search
    crawlR --> batch
    wf --> orch & search & cmp & adv & deal & link & mem
    orch --> llm
    adv --> llm
    search --> sem --> llm
    search --> enr & rank & rag & prodRepo
    enr --> shops
    search --> shops
    watch --> enr
    watch --> alertRepo & prodRepo
    batch --> search
    mem --> chatRepo
    userRepo & chatRepo & prodRepo & alertRepo --> db
    rag --> vec
```

## Danh mục thành phần

| Thành phần | Trách nhiệm | Phụ thuộc chính |
|---|---|---|
| Auth API + Auth service | Đăng ký, đăng nhập, phiên, hồ sơ, dữ liệu cá nhân | UserRepository |
| Auth dependency | Xác định người dùng từ token, kiểm tra vai trò | UserRepository |
| Chat API | Quyền sở hữu hội thoại, gọi workflow, chuyển sự kiện SSE | Agent Workflow, ChatRepository |
| Agent Workflow | Đồ thị LangGraph; hỏi làm rõ; tìm kiếm có nới lỏng / tìm thêm; gợi ý câu hỏi | Orchestrator, EcomSearch, Comparison, Advisor, DealFinder, LinkParser, Session Memory |
| Orchestrator | Ý định + tiêu chí | LLM |
| EcomSearch | Cache → RAG → cào; làm sạch; lọc; hoàn thiện | Enricher, Ranker, Semantic Filter, RAG, ProductRepository, sàn |
| Enricher | Trang chi tiết, giá hiện tại | sàn |
| Ranker | Đối chiếu thông số, điểm, lý do | — |
| Comparison | Bảng so sánh | — |
| Advisor | Ngữ cảnh chuẩn hóa, lời tư vấn | LLM, Session Memory |
| Price Watcher | Theo dõi giá, guardrails | Enricher, AlertRepository, ProductRepository |
| Batch Crawler | Làm ấm / thu thập hàng loạt | EcomSearch |
| Session Memory | Trí nhớ hội thoại, trạng thái giữa các lượt | ChatRepository |

## Luồng phụ thuộc

Route → (dependency xác thực) → agent / dịch vụ → repository → SQLite. Không thành phần nào ở tầng dưới gọi ngược lên route.

**Tiếp theo:** [C4 — Mã](04-code.md).
