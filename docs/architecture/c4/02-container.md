# C2 — Container

```mermaid
flowchart LR
    user(["👤 Người dùng / Quản trị viên"])

    subgraph sys["Shopping AI"]
        web["Web App<br/><i>[React 19, Vite, Tailwind 4]</i><br/>Giao diện, phiên đăng nhập,<br/>đọc SSE, đồng bộ dữ liệu cá nhân"]
        api["API & Agent Backend<br/><i>[Python 3.11, FastAPI, LangGraph]</i><br/>Xác thực, điều phối agent,<br/>thu thập, xếp hạng, theo dõi giá"]
        db[("CSDL quan hệ<br/><i>[SQLite]</i><br/>tài khoản, sản phẩm, lịch sử giá,<br/>hội thoại, theo dõi giá")]
        vec[("CSDL vector<br/><i>[ChromaDB]</i><br/>tìm theo ngữ nghĩa")]
    end

    llm["Dịch vụ LLM"]
    shops["Sàn TMĐT"]

    user -- "HTTPS" --> web
    web -- "REST JSON + SSE, Bearer token" --> api
    api -- "SQLAlchemy async" --> db
    api -- "chromadb client" --> vec
    api -- "API tương thích OpenAI" --> llm
    api -- "HTTP: HTML / JSON" --> shops

    style web fill:#b7791f,color:#fff
    style api fill:#b7791f,color:#fff
    style llm fill:#888,color:#fff
    style shops fill:#888,color:#fff
```

## Trách nhiệm

| Container | Trách nhiệm | Mã |
|---|---|---|
| Web App | Màn hình, hộp thoại; gọi API qua `agentApi.ts`; giữ token; đồng bộ dữ liệu cá nhân (`useSyncedState`) | `frontend/` |
| API & Agent Backend | Mọi quy tắc nghiệp vụ, xác thực, phân quyền; đồ thị LangGraph; vòng theo dõi giá và làm ấm kho chạy nền trong cùng tiến trình | `backend/` |
| CSDL quan hệ | Dữ liệu bền vững | `backend/shopai.db` |
| CSDL vector | Vector mô tả sản phẩm | `backend/chroma_db/` |

## Quy tắc kiến trúc

- Web App không chứa quy tắc nghiệp vụ quyết định; backend luôn kiểm tra lại.
- Chỉ backend giữ khóa API LLM và gọi sàn TMĐT.
- Tác vụ nền (theo dõi giá, làm ấm kho) chạy trong lifespan của backend, không tách dịch vụ riêng.

## Hiện trạng

Hai container chạy cục bộ (`:3000`, `:8000`); xem [arc42 §7](../arc42/07-deployment-view.md).

**Tiếp theo:** [C3 — Thành phần](03-component.md).
