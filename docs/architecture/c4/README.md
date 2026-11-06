# Mô hình C4 — Shopping AI

| Mức | Tài liệu | Trả lời câu hỏi |
|---|---|---|
| C1 | [Bối cảnh hệ thống](01-system-context.md) | Ai dùng, hệ thống nói chuyện với hệ thống ngoài nào? |
| C2 | [Container](02-container.md) | Gồm những ứng dụng / kho dữ liệu nào, giao tiếp ra sao? |
| C3 | [Thành phần](03-component.md) | Backend chia thành những thành phần nào? |
| C4 | [Mã](04-code.md) | Hai luồng cốt lõi được hiện thực bằng lớp nào? |

## Trạng thái triển khai

Mọi thành phần trong các sơ đồ đã có trong mã nguồn (`backend/`, `frontend/`).

## Quy ước màu

| Màu | Ý nghĩa |
|---|---|
| Hổ phách đậm | Hệ thống / container đang mô tả |
| Xám | Hệ thống ngoài |
| Trụ (cylinder) | Kho dữ liệu |
