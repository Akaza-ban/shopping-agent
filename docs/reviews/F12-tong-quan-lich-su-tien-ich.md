# F12 Tổng quan, lịch sử hoạt động & tiện ích — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Góp ý / hỗ trợ không tới được ai
> Mã chính: [`DashboardView.tsx`](../../frontend/src/components/DashboardView.tsx), [`ActivityLogView.tsx`](../../frontend/src/components/ActivityLogView.tsx), [`HelpRequestModal.tsx`](../../frontend/src/components/HelpRequestModal.tsx), [`Header.tsx`](../../frontend/src/components/Header.tsx), [`Sidebar.tsx`](../../frontend/src/components/Sidebar.tsx)

## Đã làm được

- Tổng quan: thao tác nhanh, 5 ô thống kê, tìm kiếm gần đây (mở lại trong chat), đã lưu gần đây.
- Lịch sử hoạt động: 8 loại, nhóm theo ngày, lọc, tìm, "Mở lại", xóa có xác nhận; tối đa 200 mục.
- Giao diện sáng / tối đồng nhất; thanh bên thu gọn; menu tài khoản.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Góp ý và yêu cầu hỗ trợ chỉ ghi vào lịch sử hoạt động của chính người gửi | `HelpRequestModal` → `activities` | Không ai nhận được; người dùng nghĩ đã gửi cho đội phát triển | Cao |
| 2 | Lịch sử hoạt động lưu nguyên khối trong `user_data`, cắt ở 200 mục | khóa `activities` | Mất lịch sử cũ; cùng rủi ro ghi đè như [F01](F01-tai-khoan-xac-thuc.md) #5 | Thấp |
| 3 | Nhãn không thống nhất | xem [Hệ thống nhãn](../04-information-architecture.md#hệ-thống-nhãn) | "Tra cứu bảo hành & đổi trả" / "Tra cứu chính sách bảo hành & đổi trả"; ba tên cho hộp thoại nguồn dữ liệu; "Xem tại sàn" / "Mở trang gốc" | Thấp |
| 4 | Thao tác nhanh trên Tổng quan thiếu "Theo dõi giá" | `quickActions` trong `DashboardView.tsx` | Tính năng mới khó được phát hiện | Thấp |
| 5 | Chưa tối ưu riêng cho điện thoại | — | Trải nghiệm trên màn hình nhỏ hạn chế (ngôn ngữ và giao diện: xem [F13](F13-nguon-kho-du-lieu.md) phần B) | Thấp |

## Đề xuất cải thiện

1. **Gửi góp ý thật:** bảng `feedback (id, user_id, kind, topic, content, contact, created_at, status)` + `POST /api/feedback`; quản trị viên xem danh sách; vẫn ghi vào lịch sử hoạt động để người gửi thấy. Thông báo "đã gửi tới đội phát triển" chỉ hiện khi máy chủ nhận.
2. **Thống nhất nhãn** theo bảng trong kiến trúc thông tin (sửa chuỗi trong `Header.tsx`, `Sidebar.tsx`, `SettingsModal.tsx`, `SearchAssistantView.tsx`, `SavedProductsView.tsx`).
3. Thêm "Theo dõi giá" vào thao tác nhanh.
4. Lịch sử hoạt động chuyển sang bảng riêng ở máy chủ nếu cần giữ lâu (cùng đợt với [F08](F08-quan-ly-hoi-thoai.md) #1).

## Liên quan

[UC15, UC16](../03-use-cases.md), [04-information-architecture.md](../04-information-architecture.md)
