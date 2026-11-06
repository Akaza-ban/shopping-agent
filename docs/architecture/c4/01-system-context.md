# C1 — Bối cảnh hệ thống

> **Mục đích:** cho thấy ai dùng Shopping AI và hệ thống phụ thuộc những hệ thống ngoài nào, chưa đi vào công nghệ.

```mermaid
flowchart LR
    user(["👤 Người dùng"])
    admin(["👤 Quản trị viên"])

    subgraph boundary[" "]
        sys["Shopping AI<br/><i>[Hệ thống phần mềm]</i><br/>Hiểu nhu cầu mua sắm, thu thập và kiểm chứng sản phẩm,<br/>xếp hạng, so sánh, tư vấn, theo dõi giá"]
    end

    llm["Dịch vụ LLM<br/><i>[Hệ thống ngoài]</i><br/>DeepSeek · OpenRouter · Groq"]
    shops["Sàn TMĐT<br/><i>[Hệ thống ngoài]</i><br/>Tiki · Thế Giới Di Động · Điện Máy Xanh"]

    user -- "hỏi tư vấn, so sánh, lưu, theo dõi giá" --> sys
    admin -- "quản lý nguồn và kho dữ liệu" --> sys
    sys -- "phân loại ý định, lọc, soạn lời tư vấn [HTTPS]" --> llm
    sys -- "đọc sản phẩm, thông số, giá [HTTPS]" --> shops

    style sys fill:#b7791f,color:#fff
    style llm fill:#888,color:#fff
    style shops fill:#888,color:#fff
```

## Ranh giới hệ thống

Shopping AI chịu trách nhiệm: tài khoản, hội thoại tư vấn, thu thập và kiểm chứng dữ liệu sản phẩm, xếp hạng, so sánh, săn deal, theo dõi giá, dữ liệu cá nhân.

Ngoài phạm vi: đặt hàng, thanh toán, vận chuyển, giá / tồn kho chính thức (thuộc sàn), danh tính bên thứ ba.

## Người dùng và quyền chính

| Người | Quyền chính |
|---|---|
| Người dùng | Mọi chức năng tư vấn và dữ liệu cá nhân của mình |
| Quản trị viên | Như người dùng + kích hoạt thu thập dữ liệu, xem nhật ký guardrails |

**Tiếp theo:** [C2 — Container](02-container.md).

**Nguồn:** `backend/src/main.py`, `backend/src/config.py`, [01-scope.md](../../01-scope.md).
