# Yêu cầu theo INVEST — Shopping AI V1

> Trạng thái: V1

Mỗi user story đủ nhỏ để làm và kiểm thử độc lập. Xác thực, phân quyền, kiểm tra dữ liệu và xử lý lỗi là ràng buộc nghiệm thu chung, không phải tính năng ẩn.

## Áp dụng INVEST

| Nguyên tắc | Cách áp dụng |
|---|---|
| Independent (Độc lập) | Mỗi story cho ra kết quả quan sát được; chỉ ghi phụ thuộc bắt buộc. |
| Negotiable (Thương lượng được) | Bố cục, câu chữ giao diện có thể đổi; kết quả và quyền giữ nguyên. |
| Valuable (Có giá trị) | Mỗi story nêu rõ lợi ích cho người dùng. |
| Estimable (Ước lượng được) | Đầu vào, đầu ra, vai trò, ngoại lệ được nêu rõ. |
| Small (Nhỏ) | Một khả năng; tách được thành API, dịch vụ, CSDL, giao diện. |
| Testable (Kiểm thử được) | Liên kết tới tiêu chí trong [06-acceptance-criteria.md](06-acceptance-criteria.md). |

## Product backlog

| ID | User story | Giá trị | Phụ thuộc | Tiêu chí |
|---|---|---|---|---|
| US01 | Là khách, tôi muốn đăng ký tài khoản để lưu dữ liệu mua sắm của mình. | Dữ liệu cá nhân bền vững | — | AC-UC01 |
| US02 | Là người dùng, tôi muốn đăng nhập để dùng ứng dụng trên mọi thiết bị. | Truy cập an toàn | US01 | AC-UC02 |
| US03 | Là người dùng, tôi muốn đăng xuất để thiết bị này không còn truy cập tài khoản. | An toàn phiên | US02 | AC-UC03 |
| US04 | Là người dùng, tôi muốn đổi tên hiển thị và mật khẩu để giữ tài khoản cập nhật và an toàn. | Tự phục vụ | US02 | AC-UC04 |
| US05 | Là người dùng, tôi muốn mô tả nhu cầu bằng lời để nhận sản phẩm phù hợp kèm lý do. | Tiết kiệm thời gian tìm kiếm | US02 | AC-UC05 |
| US06 | Là người dùng, tôi muốn được hỏi ngân sách khi yêu cầu còn chung để kết quả đúng phân khúc. | Kết quả sát nhu cầu | US05 | AC-UC06 |
| US07 | Là người dùng, tôi muốn xem bảng so sánh các lựa chọn để quyết định nhanh. | Quyết định có căn cứ | US05 | AC-UC07 |
| US08 | Là người dùng, tôi muốn dán link sản phẩm để được thẩm định. | Kiểm tra sản phẩm đang xem | US02 | AC-UC08 |
| US09 | Là người dùng, tôi muốn biết sản phẩm nào đang giảm sâu nhất để mua đúng lúc. | Tiết kiệm tiền | US05 | AC-UC09 |
| US10 | Là người dùng, tôi muốn tạo, chuyển, xóa hội thoại để tách các nhu cầu khác nhau. | Tổ chức công việc | US05 | AC-UC10 |
| US11 | Là người dùng, tôi muốn lưu sản phẩm và nhờ AI so sánh sau. | Quay lại dễ dàng | US05 | AC-UC11 |
| US12 | Là người dùng, tôi muốn được báo khi giá xuống mức mong muốn để không phải kiểm tra thủ công. | Mua đúng giá | US05 | AC-UC12 |
| US13 | Là người dùng, tôi muốn xem lịch sử giá để biết giá hiện tại có tốt không. | Đánh giá thời điểm mua | US12 | AC-UC13 |
| US14 | Là người dùng, tôi muốn so sánh chính sách đổi trả giữa các sàn. | Giảm rủi ro sau mua | US02 | AC-UC14 |
| US15 | Là người dùng, tôi muốn xem tổng quan và lịch sử hoạt động để mở lại kết quả cũ. | Liên tục | US05 | AC-UC15 |
| US16 | Là quản trị viên, tôi muốn kích hoạt thu thập lại dữ liệu để kho luôn mới. | Dữ liệu tươi | US02 | AC-UC16 |
| US17 | Là hệ thống, tôi muốn kiểm tra giá định kỳ để cập nhật trạng thái theo dõi mà không cần người dùng thao tác. | Tự động | US12 | AC-UC17 |
| US18 | Là người dùng, tôi muốn gửi góp ý / yêu cầu hỗ trợ. | Kênh phản hồi | US02 | AC-UC18 |

## Đánh giá INVEST từng story (tóm tắt)

| Story | I | N | V | E | S | T | Ghi chú |
|---|---|---|---|---|---|---|---|
| US01–US04 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Mỗi API một hành động; test riêng trong `test_auth.py` |
| US05 | ✓ | ✓ | ✓ | ✓ | ✗ → tách | ✓ | Lớn nhất; đã tách theo giai đoạn: Mức 1 (dữ liệu đúng), Mức 2 (xếp hạng, làm giàu, so sánh, làm rõ), Mức 3 (LangGraph) |
| US06–US11 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| US12–US13 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | US13 dùng dữ liệu do US12 / thu thập tạo ra |
| US14 | ✓ | ✓ | ✓ | ✓ | ✓ | một phần | Dữ liệu tham khảo; kiểm thử thủ công |
| US15–US18 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |

## Ràng buộc nghiệm thu chung

- Mọi API trừ đăng ký / đăng nhập yêu cầu token hợp lệ (`401`).
- Dữ liệu cá nhân chỉ chủ sở hữu truy cập (`403` / `404`).
- Thông báo lỗi trả `detail` tiếng Việt.
- Trợ lý không trình bày giá / thông số ngoài dữ liệu thu thập.
