# Rà soát tính năng & hướng cải thiện

> Ngày 30/10/2026 · Đối chiếu mã nguồn `backend/`, `frontend/` với [02-features.md](../02-features.md)
>
> Mức: ✅ Tốt · 🟡 Chạy được, cần cải thiện · 🔴 Nên ưu tiên (đang gây sai lệch cho người dùng)

Mỗi tệp gồm: **đã làm được**, **vấn đề** (ở đâu trong mã, ảnh hưởng, mức độ), **đề xuất cải thiện** kèm cách kiểm chứng.

## Tổng hợp

| Tính năng | Mức | Vấn đề chính |
|---|---|---|
| [F01 Tài khoản & xác thực](F01-tai-khoan-xac-thuc.md) | 🟡 | Không giới hạn tần suất gọi tư vấn; bộ đếm đăng nhập sai trong RAM; dữ liệu cá nhân ghi đè nguyên khối |
| [F02 Tư vấn mua sắm](F02-tu-van-mua-sam.md) | 🟡 | Chưa có bộ đánh giá câu trả lời; dữ liệu cào đi thẳng vào prompt (prompt injection) |
| [F03 Hỏi làm rõ](F03-hoi-lam-ro.md) | 🟡 | Chỉ hỏi ngân sách; mức ngân sách cố định |
| [F04 Tìm kiếm & thu thập](F04-tim-kiem-thu-thap.md) | 🔴 | TGDĐ / ĐMX chỉ ~20 sản phẩm đầu; đã bỏ Shopee / Lazada; kết quả không biết còn hàng |
| [F05 Xếp hạng & nới lỏng](F05-xep-hang-noi-long.md) | 🟡 | Trọng số đặt tay chưa đo; khớp thông số theo chuỗi |
| [F06 So sánh sản phẩm](F06-so-sanh-san-pham.md) | 🟡 | So sánh đã lưu không có lời tư vấn; thiếu hàng thông số theo ngành |
| [F07 Săn deal & thẩm định link](F07-san-deal-tham-dinh-link.md) | 🟡 | Tin giá gốc của sàn (giảm giá ảo); chưa dùng lịch sử giá; link chưa so giá nơi khác |
| [F08 Quản lý hội thoại](F08-quan-ly-hoi-thoai.md) | 🟡 | Cả hội thoại trong một khóa 2 MB, tối đa 30; ghi lượt chat bằng task nền không chờ |
| [F09 Sản phẩm đã lưu](F09-san-pham-da-luu.md) | 🟡 | Giá lúc lưu không được làm mới |
| [F10 Theo dõi giá](F10-theo-doi-gia.md) | ✅ | Chỉ báo trong ứng dụng (chưa có email); kiểm tra tuần tự dưới một khóa chung |
| [F11 Tra cứu chính sách](F11-tra-cuu-chinh-sach.md) | 🔴 | Dữ liệu mẫu cố định trong frontend; "Tra cứu bằng AI" chỉ mô phỏng |
| [F12 Tổng quan & tiện ích](F12-tong-quan-lich-su-tien-ich.md) | 🟡 | Góp ý / hỗ trợ không gửi tới ai; nhãn chưa thống nhất |
| [F13 Nguồn & kho dữ liệu, cài đặt](F13-nguon-kho-du-lieu.md) | 🔴 | Cấu hình nguồn (lẽ ra chỉ quản trị viên) đang mở cho mọi người dùng và không được lưu / áp dụng ở máy chủ; người dùng chưa có cài đặt giao diện theo giờ và ngôn ngữ tiếng Anh |

## Thứ tự đề xuất

**Đợt 1 — sửa những chỗ đang làm người dùng hiểu sai (việc nhỏ, làm ngay)**

1. [F13](F13-nguon-kho-du-lieu.md) phần A: chuyển cấu hình nguồn thành chức năng của quản trị viên (ẩn với người dùng, lưu ở máy chủ, áp dụng cho mọi lượt tìm kiếm).
2. ✅ [F13](F13-nguon-kho-du-lieu.md) phần B: hộp thoại "Cài đặt" cho người dùng, chỉ gồm thiết lập lõi — giao diện (sáng / tối / theo giờ) và ngôn ngữ (Tiếng Việt / English). *Đã làm 30/10/2026.*
3. [F11](F11-tra-cuu-chinh-sach.md) đề xuất 1: ghi rõ dữ liệu tham khảo, bỏ tiến trình giả.
4. [F12](F12-tong-quan-lich-su-tien-ich.md) #1: góp ý gửi về máy chủ; thống nhất nhãn.
5. [F01](F01-tai-khoan-xac-thuc.md) #2: giới hạn tần suất gọi tư vấn theo tài khoản.

**Đợt 2 — chất lượng tư vấn**

6. [F02](F02-tu-van-mua-sam.md) #1: bộ đánh giá câu trả lời; chống prompt injection.
7. [F07](F07-san-deal-tham-dinh-link.md) #1: kiểm định deal bằng lịch sử giá.
8. [F04](F04-tim-kiem-thu-thap.md) #4: đọc còn hàng ở bước làm giàu.
9. [F05](F05-xep-hang-noi-long.md) #1–#2: chuẩn hóa thông số, bộ đánh giá xếp hạng.

**Đợt 3 — mở rộng và bền vững**

10. [F10](F10-theo-doi-gia.md) #1: thông báo email (dùng chung cho quên mật khẩu ở F01).
11. [F04](F04-tim-kiem-thu-thap.md) #1–#2: Playwright cho TGDĐ / ĐMX, thêm nguồn.
12. [F08](F08-quan-ly-hoi-thoai.md) #1, [F09](F09-san-pham-da-luu.md) #2: chuyển hội thoại / đã lưu về bảng ở máy chủ.
13. [F11](F11-tra-cuu-chinh-sach.md) đề xuất 2–3: chính sách ở backend + RAG chính sách.

## Liên quan

- [10-feature-status.md](../10-feature-status.md): bảng đã có / một phần / chưa có.
- [arc42 §11 Rủi ro và nợ kỹ thuật](../architecture/arc42/11-risks-and-technical-debt.md).
- [11-rag.md](../11-rag.md): RAG sản phẩm và kết quả đánh giá.
