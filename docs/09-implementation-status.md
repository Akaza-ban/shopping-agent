# Trạng thái triển khai và kiểm thử

> Cập nhật: 29/10/2026

## Nguồn sự thật

| Nội dung | Nguồn |
|---|---|
| Hợp đồng API | [api/openapi.json](api/openapi.json) (xuất từ `backend/src/main.py`) |
| Lược đồ dữ liệu | `backend/database/models/*.py` → [05-data-model.md](05-data-model.md) |
| Luồng agent | `backend/core/graph.py` → [arc42 §6](architecture/arc42/06-runtime-view.md) |
| Quy tắc nghiệp vụ | [requirements/business-rules.md](requirements/business-rules.md) |
| Bằng chứng nghiệm thu | `backend/tests/` → [06-acceptance-criteria.md](06-acceptance-criteria.md) |

## Các giai đoạn đã thực hiện

| Giai đoạn | Nội dung | Kết quả |
|---|---|---|
| Giao diện mẫu | Tái cấu trúc `frontend`: tổng quan, tư vấn, so sánh trong chat, đã lưu, lịch sử, tra cứu chính sách | Hoàn thành |
| Mức 1 — Dữ liệu đúng | Bộ phân tích TGDĐ/ĐMX không phụ thuộc tên class, lọc phụ kiện Tiki, nới lỏng tiêu chí trung thực, chuỗi dự phòng LLM | Hoàn thành |
| Mức 2 — Chất lượng tư vấn | Xếp hạng có lý do, làm giàu trang chi tiết, bảng so sánh, độ mới dữ liệu, hỏi làm rõ | Hoàn thành |
| Mức 3 — Kiến trúc | Chuyển sang LangGraph `StateGraph`, sửa tham số `platform`, săn deal thật, nối frontend với backend, dọn mã trùng | Hoàn thành |
| Hội thoại | Tạo / chuyển / xóa hội thoại, xóa trí nhớ phiên ở máy chủ | Hoàn thành |
| Giao diện | Thanh bên mới, chế độ sáng / tối đồng nhất | Hoàn thành |
| Theo dõi giá | Bảng `price_alerts`, đọc giá thật, guardrails, lịch sử giá, kho dữ liệu | Hoàn thành |
| Tài khoản | Đăng ký / đăng nhập, phân quyền, dữ liệu theo tài khoản | Hoàn thành |
| RAG | Embedding bge-m3 qua API, BM25 + RRF, chuẩn hóa danh mục, độ mới, bộ đánh giá, nạp lại kho `products_v2` | Hoàn thành (trừ RAG chính sách) |

## Bộ kiểm thử tự động

147 test trong 20 tệp (`backend/tests/`). Lệnh: `cd backend && pytest`.

| Tệp | Số test | Phạm vi |
|---|---|---|
| `test_rag.py` | 41 | Danh mục theo mã sàn, embedding giả lập, BM25 / RRF, độ mới, dự phòng khi API lỗi, bộ đánh giá (1 test đo trên kho thật chỉ chạy khi `RUN_LIVE_TESTS=1`) |
| `test_auth.py` | 10 | Xác thực, phân quyền, dữ liệu cá nhân |
| `test_architecture_level3.py` | 9 | Đồ thị LangGraph, stream, khôi phục trạng thái, săn deal, xóa hội thoại |
| `test_advisor_level2.py` | 13 | Trang chi tiết, xếp hạng, so sánh, hỏi làm rõ |
| `test_search_level1.py` | 10 | Phân tích trang danh sách, lọc Tiki, nới lỏng (1 test cào trực tiếp chỉ chạy khi `RUN_LIVE_TESTS=1`) |
| `test_price_alerts.py` | 15 | Đọc giá và tình trạng còn hàng, theo dõi giá, xác nhận giá mới, đọc lại trước khi báo, hết hàng, nhật ký kiểm tra, nâng cấp bảng |
| `test_database_schema.py`, `test_product_repository.py` | 8 | CSDL, lịch sử giá, cache |
| `test_data_processor.py`, `test_semantic_filter.py`, `test_guardrails.py` | 22 | Làm sạch dữ liệu, lọc ngữ nghĩa, luật guardrails giá |
| `test_agents.py`, `test_shopping_advisor_*.py` | 7 | Router, advisor, câu trả lời dự phòng |
| `test_batch_crawler.py`, `test_cache_first_search.py`, `test_tgdd_dmx_integration.py`, `test_multi_platform_search.py`, `test_api_client.py` | 12 | Thu thập hàng loạt, cache-first, tích hợp sàn thật |

**Kết quả 29/10/2026:** toàn bộ đạt, trừ 1 test bỏ qua theo cờ. Ghi chú:

- Các test tích hợp sàn thật và test gọi LLM thật (`test_tgdd_dmx_integration`, `test_batch_crawler`, `test_agents::test_orchestrator_and_advisor_flow`, `test_cache_first_search::test_cache_first_performance_boost`) phụ thuộc mạng / LLM / tải máy nên có thể lỗi ngẫu nhiên; chạy lại riêng thì đạt.
- Không chạy bộ test cùng lúc với máy chủ đang ghi `shopai.db` (SQLite báo `database is locked`).
- `tests/conftest.py` cho các test API cũ chạy dưới một quản trị viên giả; `test_auth.py` dùng xác thực thật trên SQLite tạm.

## Kiểm thử đầu-cuối (E2E)

Chạy backend thật + bản build frontend, điều khiển Edge headless qua Chrome DevTools Protocol.

| Bước | Kịch bản | Kết quả |
|---|---|---|
| 1 | Chưa đăng nhập → màn đăng nhập | Đạt |
| 2 | Đăng ký với dữ liệu sai → báo lỗi tên, email, mật khẩu yếu, nhập lại không khớp | Đạt |
| 3 | Đăng ký hợp lệ → vào thẳng ứng dụng | Đạt |
| 4–5 | Gửi góp ý; menu tài khoản hiện email và Đăng xuất | Đạt |
| 6 | Đăng xuất → về màn đăng nhập, xóa token | Đạt |
| 7 | Sai mật khẩu → "Email hoặc mật khẩu không đúng" | Đạt |
| 8 | Tài khoản thứ hai không thấy dữ liệu của tài khoản thứ nhất | Đạt |
| 9 | Xóa dữ liệu trên máy, đăng nhập lại → dữ liệu tải từ máy chủ | Đạt |
| 10 | Tải lại trang giữ phiên | Đạt |

Các luồng tư vấn đã thử với dữ liệu thật: hỏi làm rõ "máy giặt" → chọn 5–10 triệu → 4 máy Inverter tại ĐMX; "Laptop gaming dưới 25 triệu có RTX 4050" → phát hiện máy dùng RTX 3050, gắn nhãn sai cấu hình, tìm thêm tới 30 triệu và ghi chú; săn deal tai nghe Sony; theo dõi giá laptop TGDĐ đọc được 22.990.000 ₫ và chuyển "Đã đạt giá".

## Hạn chế đã biết

Xem [arc42 §11](architecture/arc42/11-risks-and-technical-debt.md).

## Lộ trình tiếp theo

1. Playwright cho trang render bằng JavaScript (đủ danh sách TGDĐ).
2. Thông báo email / đẩy khi đạt giá (đã có cột `user_email`).
3. Thu thập tự động chính sách đổi trả.
4. Quên mật khẩu qua email; quản trị người dùng.
5. Chuyển sang PostgreSQL và Alembic khi triển khai nhiều worker.
