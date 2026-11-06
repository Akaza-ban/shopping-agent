# Yêu cầu phi chức năng — Shopping AI V1

> Trạng thái: V1 — số đo lấy từ kiểm thử tự động và các lần chạy thật

| ID | Thuộc tính | Yêu cầu | Đo / kiểm chứng | Hiện trạng |
|---|---|---|---|---|
| NFR-01 | Hiệu năng — cache | Kết quả có trong cache trả về < 0,15 giây | `test_cache_first_search::test_cache_first_performance_boost` | Đạt (có thể chậm khi máy tải nặng) |
| NFR-02 | Hiệu năng — tư vấn | Lượt tư vấn phải cào mới hoàn tất trong 30 giây; có phản hồi tiến trình đầu tiên < 3 giây | Đo thực tế: 14 s (máy giặt), 22 s (tai nghe); sự kiện `routing` gửi ngay | Đạt; bước "tìm thêm" có thể cộng thêm ~10 s |
| NFR-03 | Hiệu năng — hỏi làm rõ | Câu hỏi làm rõ < 5 giây | Đo thực tế ≈ 2,5 s | Đạt |
| NFR-04 | Tính sẵn sàng | Không trả trang trắng khi LLM lỗi | Chuỗi DeepSeek → OpenRouter → Groq + câu trả lời dựng sẵn; `test_shopping_advisor_full::test_step4_zero_crash_fallback_on_error` | Đạt |
| NFR-05 | Độ bền trạng thái | Câu hỏi làm rõ đang chờ, hội thoại, theo dõi giá còn sau khởi động lại | `test_architecture_level3::test_pending_clarification_survives_restart` | Đạt |
| NFR-06 | Bảo mật — xác thực | Mật khẩu bcrypt; token chỉ lưu dạng băm; khóa sau 5 lần sai | `test_auth.py` | Đạt |
| NFR-07 | Bảo mật — phân quyền | Không đọc / sửa được dữ liệu người khác | `test_auth::test_conversations_are_private`, `test_price_alerts_are_private`, `test_user_data_sync` | Đạt |
| NFR-08 | Bảo mật — bí mật | Khóa API LLM chỉ ở `.env` máy chủ, không xuống trình duyệt, không ghi log | Rà soát mã | Đạt |
| NFR-09 | Bảo mật — hiển thị | Nội dung LLM không chèn HTML trực tiếp | `Markdown.tsx` dựng phần tử React | Đạt |
| NFR-10 | Tính đúng dữ liệu | Không báo đạt giá với giá bất thường; không hiển thị giá vô lý trong kết quả | `test_price_alerts::*`, `test_guardrails::*` | Đạt |
| NFR-11 | Khả năng bảo trì | Bộ phân tích trang sàn có test hồi quy bằng trang thật lưu sẵn | Fixtures `tests/fixtures/*.html` | Đạt |
| NFR-12 | Khả năng sử dụng | Thấy tiến trình theo thời gian thực; trạng thái có chữ + biểu tượng; chế độ sáng / tối | Kiểm thử giao diện, ảnh chụp | Đạt |
| NFR-13 | Tương thích | Trình duyệt hiện đại; Windows / Linux / macOS cho backend | Python 3.11, Node ≥ 20.11 | Đạt |
| NFR-14 | Khả năng mở rộng | Thêm sàn / LLM không sửa tầng khác | Kiến trúc phân tầng, chuỗi `with_fallbacks` | Đạt |

## Tải tham chiếu

V1 hướng tới một máy chủ, một tiến trình (`uvicorn`), vài người dùng đồng thời (đồ án / demo). SQLite phù hợp mức tải này; nhiều worker cần chuyển PostgreSQL (trạng thái chờ làm rõ và bộ đếm đăng nhập sai đang có phần nằm trong RAM của tiến trình).

## Chưa có chính sách vận hành

- Thời gian giữ lịch sử hội thoại, lịch sử giá, token hết hạn (chưa dọn định kỳ).
- Sao lưu `shopai.db` và `chroma_db/`.
- Giới hạn tần suất gọi API tư vấn theo người dùng (chi phí LLM).
