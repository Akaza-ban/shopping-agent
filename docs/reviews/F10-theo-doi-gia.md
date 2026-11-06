# F10 Theo dõi giá & lịch sử giá — đánh giá

> Rà soát ngày 30/10/2026 · Mức: ✅ Vừa gia cố guardrails, còn thiếu kênh thông báo
> Mã chính: [`backend/services/pricing/watcher.py`](../../backend/services/pricing/watcher.py), [`backend/services/pricing/guardrails.py`](../../backend/services/pricing/guardrails.py), [`backend/src/routes/alerts.py`](../../backend/src/routes/alerts.py), [`frontend/src/components/PriceAlertsView.tsx`](../../frontend/src/components/PriceAlertsView.tsx)

## Đã làm được

- Tạo / xem / bỏ theo dõi; gợi ý mức −5 … −20%; kiểm tra định kỳ (6 giờ) và "Kiểm tra ngay".
- Đọc giá thật (JSON-LD TGDĐ / ĐMX, API Tiki) và tình trạng còn hàng.
- Guardrails (BR-011): giá gốc do server đọc; giá vô lý bị bỏ qua; biến động lớn chờ xác nhận ở lần đọc sau; giảm mạnh tới mức mong muốn thì đọc lại; hết hàng không báo.
- Lịch sử giá (biểu đồ + bảng); nhật ký kiểm tra lưu bảng `price_checks`.
- Test: `tests/test_price_alerts.py` (15), `tests/test_guardrails.py` (15).

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Chỉ báo trong ứng dụng | — (cột `user_email` có nhưng chưa dùng) | Người dùng phải mở ứng dụng mới biết đạt giá → mất cơ hội mua | Cao |
| 2 | Kiểm tra tuần tự dưới một khóa chung cho mọi người dùng | `self._lock`, vòng `for alert in watching` trong `check_alerts` | Nhiều yêu cầu → "Kiểm tra ngay" của người này phải chờ của người khác; mỗi trang 1–5 s | Trung bình |
| 3 | Không sửa được giá mong muốn | không có `PATCH /api/alerts/{id}` | Phải bỏ theo dõi rồi tạo lại, mất lịch sử nhật ký | Thấp |
| 4 | Lịch sử giá chỉ có mốc khi hệ thống tình cờ đọc | `upsert_products` ghi mốc khi giá đổi | Biểu đồ thưa với sản phẩm ít người xem | Thấp |
| 5 | Vòng nền chạy trong tiến trình web | `lifespan` trong `src/main.py` | Nhiều worker → mỗi worker một vòng, kiểm tra trùng | Thấp |
| 6 | Đạt giá là trạng thái cuối | `status = triggered` | Giá xuống tiếp không được báo; muốn theo dõi tiếp phải tạo lại | Thấp |

## Đề xuất cải thiện

1. **Thông báo email** khi `triggered` (và tùy chọn khi hàng về): dịch vụ SMTP / API gửi thư cấu hình trong `.env`; hàng đợi gửi lưu SQLite, thử lại khi lỗi; người dùng bật / tắt trong hộp thoại Tài khoản. Kiểm chứng bằng bộ gửi giả trong test.
2. **Kiểm tra song song có giới hạn:** `asyncio.Semaphore(4)` theo sàn; khóa theo yêu cầu thay vì khóa chung.
3. **`PATCH /api/alerts/{id}`** đổi giá mong muốn (vẫn phải thấp hơn giá server đọc); tùy chọn "tiếp tục theo dõi sau khi đạt giá".
4. **Mốc giá đều đặn** cho sản phẩm đang được theo dõi (mỗi lần kiểm tra ghi mốc kể cả khi giá không đổi, hoặc 1 mốc/ngày) để biểu đồ liền mạch.
5. Tách vòng nền ra tiến trình riêng khi chạy nhiều worker (cùng lúc với chuyển PostgreSQL).

## Liên quan

[BR-010, BR-011, BR-012](../requirements/business-rules.md), [UC12, UC13, UC17](../03-use-cases.md), [F07](F07-san-deal-tham-dinh-link.md)
