# 11. Rủi ro và nợ kỹ thuật

## 11.1 Rủi ro kiến trúc

| ID | Rủi ro | Mức | Giảm thiểu hiện có | Việc cần làm |
|---|---|---|---|---|
| R-01 | Sàn đổi cấu trúc HTML / chặn truy cập | Cao | Bộ phân tích theo cấu trúc, thử lại, nhiều nguồn, fixture hồi quy | Theo dõi test live định kỳ; Playwright dự phòng |
| R-02 | LLM trả JSON hỏng hoặc "bịa" | Cao | Phân loại từ khóa dự phòng; advisor chỉ thấy dữ liệu chuẩn hóa; quy tắc trong prompt | Đánh giá chất lượng câu trả lời có hệ thống |
| R-03 | Chi phí LLM tăng theo người dùng | Trung bình | Cache nhiều tầng; số lần gọi LLM cố định mỗi lượt | Giới hạn tần suất theo tài khoản |
| R-04 | SQLite khóa khi nhiều tiến trình ghi | Trung bình | Một worker | PostgreSQL khi mở rộng |
| R-05 | Lộ khóa API | Cao | Chỉ trong `.env`, không ghi log | Quản lý bí mật khi triển khai |
| R-06 | Vi phạm điều khoản sàn khi cào nhiều | Trung bình | Cache, giới hạn đồng thời, tắt nguồn chống bot | Xin API chính thức nếu thương mại hóa |
| R-08 | Nhà cung cấp LLM chính không kết nối được từ máy chủ | Cao | Kiểm tra TCP trước khi gọi, bỏ qua nhà hỏng, chuyển dự phòng ngay | Theo dõi tỉ lệ dùng dự phòng; giữ ít nhất 2 nhà cung cấp có khóa hợp lệ |
| R-07 | Embedding API (OpenRouter) chậm hoặc ngừng | Trung bình | Timeout truy vấn 8 s, cache truy vấn, tạm ngừng 60 s sau lỗi, dự phòng BM25, cuối cùng cào trực tiếp | Theo dõi độ trễ; cân nhắc mô hình cục bộ nếu cần chạy không có mạng |

## 11.2 Nợ kỹ thuật

| ID | Nợ | Ảnh hưởng |
|---|---|---|
| TD-01 | Trang danh mục TGDĐ chỉ có sẵn ~20 sản phẩm đầu (phần sau render bằng JavaScript) | Có thể bỏ sót mẫu phù hợp |
| TD-02 | Đã bỏ Shopee / Lazada | Thiếu hai nguồn lớn |
| TD-03 | Tra cứu chính sách đổi trả dùng dữ liệu tham khảo | Có thể không khớp chính sách hiện hành |
| TD-04 | Bộ đếm đăng nhập sai, bộ nhớ đệm hội thoại trong RAM | Không an toàn khi chạy nhiều worker |
| TD-05 | Dữ liệu cá nhân ghi đè nguyên khối; mất thay đổi nếu đăng xuất trong 0,8 s | Hiếm, nhưng có thể mất thao tác cuối |
| TD-06 | Không dọn token hết hạn, không chính sách giữ dữ liệu | Bảng `auth_tokens`, lịch sử phình dần |
| TD-07 | `PRAGMA foreign_keys` chưa bật | Cascade khai báo nhưng không tự chạy |
| TD-08 | Chưa có thông báo email khi đạt giá | Người dùng phải mở ứng dụng mới biết |
| TD-09 | Test tích hợp phụ thuộc mạng / LLM thật | Có thể lỗi ngẫu nhiên trong CI |
| TD-10 | Thư mục `_legacy/` còn mã cũ | Gây nhầm lẫn; có thể xóa |
| TD-11 | Ngưỡng RAG hiệu chỉnh trên bộ đánh giá nhỏ (51 truy vấn, kho 202 sản phẩm) | Có thể cần chỉnh lại khi kho lớn lên |
| TD-12 | Vector RAG không cập nhật giá khi vòng theo dõi giá đọc được giá mới | Kết quả từ kho có thể hiển thị giá cũ hơn (đã ghi chú độ mới) |

## 11.3 Trạng thái quyết định

Các quyết định đã áp dụng: [09-architecture-decisions.md](09-architecture-decisions.md). Lộ trình xử lý nợ: [09-implementation-status.md](../../09-implementation-status.md#lộ-trình-tiếp-theo).
