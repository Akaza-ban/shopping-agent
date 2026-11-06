# F09 Sản phẩm đã lưu — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Đơn giản, dữ liệu dễ cũ
> Mã chính: [`frontend/src/components/SavedProductsView.tsx`](../../frontend/src/components/SavedProductsView.tsx), khóa `saved-products` qua [`useSyncedState.ts`](../../frontend/src/hooks/useSyncedState.ts)

## Đã làm được

- Lưu / bỏ lưu từ thẻ sản phẩm và bảng so sánh; tìm theo tên, hãng, câu tìm kiếm.
- Chọn ≥ 2 để "Nhờ AI so sánh"; theo dõi giá ngay từ thẻ đã lưu.
- Đồng bộ theo tài khoản.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Lưu nguyên bản chụp sản phẩm lúc lưu (giá, còn hàng) | dữ liệu `saved-products` | Vài ngày sau giá hiển thị đã sai; người dùng có thể quyết định dựa trên giá cũ | Trung bình |
| 2 | Chỉ nằm ở frontend + `user_data`, máy chủ không biết sản phẩm nào được lưu | — | Không thể nhắc khi sản phẩm đã lưu giảm giá; không dùng được làm tín hiệu xếp hạng | Thấp |
| 3 | Ghi đè nguyên khối khi đồng bộ | `PUT /api/auth/me/data/saved-products` | Lưu trên hai thiết bị cùng lúc có thể mất một bên ([F01](F01-tai-khoan-xac-thuc.md) #5) | Thấp |
| 4 | Không có nhóm / ghi chú | — | Khó quản lý khi lưu nhiều | Thấp |

## Đề xuất cải thiện

1. **Hiển thị độ mới và làm mới giá:** ghi "Giá lúc lưu (n ngày trước)"; nút "Cập nhật giá" đọc giá hiện tại (`fetch_current_price` qua một API mới `POST /api/products/refresh`) cho các mục đã chọn, qua guardrails.
2. **Bảng `saved_products (user_id, product_id, saved_at, note)`** ở máy chủ thay cho khóa `user_data`; sản phẩm tham chiếu bảng `products` nên luôn lấy được giá mới nhất đã biết.
3. Gợi ý "Theo dõi giá" cho sản phẩm đã lưu lâu mà chưa mua.

## Liên quan

[UC11](../03-use-cases.md), [F06](F06-so-sanh-san-pham.md), [F10](F10-theo-doi-gia.md)
