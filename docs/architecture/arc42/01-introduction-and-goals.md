# 1. Giới thiệu và mục tiêu

## 1.1 Tổng quan yêu cầu

### Vấn đề

Chọn mua đồ công nghệ, điện máy theo nhu cầu cụ thể đòi hỏi mở nhiều sàn, đọc từng trang chi tiết, so sánh bảo hành / đổi trả và theo dõi giá nhiều ngày. Chatbot tổng quát trả lời trôi chảy nhưng giá và cấu hình không được kiểm chứng.

### Mục tiêu nghiệp vụ (V1)

Một **AI Agent** hiểu nhu cầu bằng ngôn ngữ tự nhiên, **dùng công cụ** để thu thập dữ liệu thật, lọc, kiểm chứng, xếp hạng, so sánh, rồi đưa lời khuyên **có căn cứ**; kèm theo các tiện ích lưu sản phẩm, theo dõi giá, tra cứu chính sách, dữ liệu theo tài khoản.

### Phạm vi chức năng

F01 Tài khoản · F02 Tư vấn · F03 Hỏi làm rõ · F04 Thu thập dữ liệu · F05 Xếp hạng & nới lỏng · F06 So sánh · F07 Săn deal & thẩm định link · F08 Hội thoại · F09 Đã lưu · F10 Theo dõi giá · F11 Tra cứu chính sách · F12 Tổng quan & lịch sử · F13 Nguồn & kho dữ liệu. Chi tiết: [02-features.md](../../02-features.md).

### Ngoài phạm vi

Đặt hàng / thanh toán, Shopee / Lazada, thông báo email, đăng nhập mạng xã hội, quản trị người dùng. Xem [01-scope.md](../../01-scope.md).

## 1.2 Mục tiêu chất lượng

| Ưu tiên | Mục tiêu | Ý nghĩa |
|---|---|---|
| 1 | **Trung thực dữ liệu** | Không trình bày giá / thông số ngoài dữ liệu thu thập; nói rõ khi dữ liệu không chắc chắn |
| 2 | **Bảo mật & riêng tư** | Dữ liệu cá nhân chỉ chủ sở hữu truy cập; bí mật chỉ ở máy chủ |
| 3 | **Phản hồi nhanh, minh bạch** | Thấy tiến trình ngay; cache trả < 0,15 s; tư vấn mới ≤ 30 s |
| 4 | **Bền vững trước lỗi ngoài** | LLM / sàn lỗi không làm hỏng trải nghiệm |
| 5 | **Dễ bảo trì** | Sàn đổi giao diện phát hiện được bằng test; thêm nguồn không đụng tầng khác |

## 1.3 Các bên liên quan

| Vai trò | Mong đợi |
|---|---|
| Người dùng mua sắm | Lời khuyên đúng, nhanh, dễ so sánh; dữ liệu của mình được giữ riêng |
| Quản trị viên | Kho dữ liệu luôn mới; kiểm soát việc thu thập |
| Nhóm phát triển | Kiến trúc rõ, test hồi quy, tài liệu đồng bộ với mã |
| Giảng viên học phần | Đủ các sản phẩm phân tích – thiết kế: use case, UML, CSDL, kiểm thử |
| Nhà cung cấp LLM / sàn TMĐT | Hệ thống ngoài; không có thỏa thuận tích hợp |
