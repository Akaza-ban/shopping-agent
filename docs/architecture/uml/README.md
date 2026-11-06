# UML chi tiết — Shopping AI

| Tài liệu | Nội dung |
|---|---|
| [01-class-diagrams.md](01-class-diagrams.md) | Lớp dữ liệu agent, tài khoản, theo dõi giá, frontend |
| [02-sequence-diagrams.md](02-sequence-diagrams.md) | 16 biểu đồ trình tự: đăng ký, đăng xuất, đổi mật khẩu, tư vấn (SSE), hỏi làm rõ, so sánh sản phẩm đã lưu, thẩm định link, săn deal, tạo / chuyển / xóa hội thoại, lưu sản phẩm, tạo & kiểm tra theo dõi giá, lịch sử giá, tra cứu chính sách, thu thập dữ liệu |
| [03-activity-diagrams.md](03-activity-diagrams.md) | Quy trình nghiệp vụ, một lượt tư vấn, khởi động & cổng đăng nhập, lịch sử hoạt động & góp ý |

Sơ đồ use case tổng quan và phân rã mức 2 nằm trong [03-use-cases.md](../../03-use-cases.md); bảng "use case → sơ đồ" ở cuối tệp đó.

## Quan hệ với C4 và arc42

- C4 mức 3–4 cho biết **thành phần nào** tham gia; UML cho biết **lớp và thông điệp cụ thể**.
- Luồng thời gian chạy tổng quát nằm ở [arc42 §6](../arc42/06-runtime-view.md); tài liệu này đi sâu từng API.
- Sơ đồ PlantUML (dạng ảnh) dùng trong báo cáo học phần IT4082 được sinh từ cùng mô hình.
