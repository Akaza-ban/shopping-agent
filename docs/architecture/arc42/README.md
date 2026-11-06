# Shopping AI — Tài liệu kiến trúc arc42

Tài liệu theo khung [arc42](https://arc42.org). Các sơ đồ dùng Mermaid (hiển thị trực tiếp trên GitHub / VS Code).

## Mục lục

1. [Giới thiệu và mục tiêu](01-introduction-and-goals.md)
2. [Ràng buộc kiến trúc](02-architecture-constraints.md)
3. [Bối cảnh và phạm vi](03-context-and-scope.md)
4. [Chiến lược giải pháp](04-solution-strategy.md)
5. [Góc nhìn khối xây dựng](05-building-block-view.md)
6. [Góc nhìn thời gian chạy](06-runtime-view.md)
7. [Góc nhìn triển khai](07-deployment-view.md)
8. [Khái niệm xuyên suốt](08-crosscutting-concepts.md)
9. [Quyết định kiến trúc (ADR)](09-architecture-decisions.md)
10. [Yêu cầu chất lượng](10-quality-requirements.md)
11. [Rủi ro và nợ kỹ thuật](11-risks-and-technical-debt.md)
12. [Thuật ngữ](12-glossary.md)

## Mốc hiện tại

- Backend FastAPI + LangGraph chạy được, 29 operation (xem [OpenAPI](../../api/openapi.json)).
- Frontend React gọi API thật, có đăng nhập, dữ liệu theo tài khoản.
- 147 test tự động; kiểm thử đầu-cuối bằng trình duyệt headless.

Liên quan: [C4](../c4/README.md), [UML](../uml/README.md), [truy vết](../../traceability/master-traceability.md).
