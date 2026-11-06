# F13 Nguồn & kho dữ liệu, cài đặt — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🔴 Ưu tiên — cấu hình hệ thống đang mở cho mọi người dùng và không có tác dụng
> Mã chính: [`frontend/src/App.tsx`](../../frontend/src/App.tsx), [`Sidebar.tsx`](../../frontend/src/components/Sidebar.tsx), [`Header.tsx`](../../frontend/src/components/Header.tsx), [`SettingsModal.tsx`](../../frontend/src/components/SettingsModal.tsx), [`DataWarehousePanel.tsx`](../../frontend/src/components/DataWarehousePanel.tsx), [`backend/services/catalog/batch_crawler.py`](../../backend/services/catalog/batch_crawler.py), [`backend/src/routes/crawler.py`](../../backend/src/routes/crawler.py)

## Thiết kế đúng

| | Cấu hình nguồn & kho dữ liệu | Cài đặt người dùng |
|---|---|---|
| Ai dùng | **Chỉ quản trị viên** | Mọi người dùng |
| Phạm vi | Toàn hệ thống: sàn nào được thu thập, làm ấm kho, thu thập lại | Chỉ thiết lập lõi của hệ thống: **giao diện** (sáng / tối / tự đổi theo giờ trong ngày) và **ngôn ngữ** (Tiếng Việt / English). Không chứa tùy chọn của từng tính năng (theo dõi giá, tư vấn…) |
| Lưu ở | Máy chủ (CSDL), áp dụng cho mọi lượt tìm kiếm | Theo tài khoản (`user_data`), đồng bộ nhiều thiết bị |

## Hiện trạng

- Hộp thoại "Nguồn & kho dữ liệu" (DLG-02) gồm bật / tắt sàn + tình trạng kho; chỉ nút "Thu thập lại dữ liệu ngay" giới hạn cho quản trị viên.
- Làm ấm kho khi khởi động nếu dữ liệu cũ hơn 12 giờ; quản trị viên kích hoạt thu thập lại.
- Kho RAG có nạp lại (`scripts/rag/reindex.py`), dọn bản ghi cũ / sàn tắt, dọn giá sai (`scripts/catalog/clean_bad_prices.py`).
- Sàn được cào cố định là Tiki, TGDĐ, ĐMX; Shopee / Lazada đã bỏ.
- Người dùng chưa có màn hình cài đặt riêng. Nút sáng / tối nằm trên thanh tiêu đề (`useTheme`: lần đầu theo hệ điều hành, sau đó nhớ lựa chọn trong trình duyệt, không theo tài khoản); chưa có chế độ tự đổi theo giờ; giao diện chỉ có tiếng Việt (chuỗi viết thẳng trong component, chưa có i18n).

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Mọi người dùng mở được và bật / tắt nguồn dữ liệu | Mục "Cài đặt nguồn dữ liệu" (`Sidebar.tsx`), nút "Nguồn dữ liệu: N nền tảng" (`Header.tsx`), `SettingsModal.tsx` không kiểm tra vai trò | Người dùng thấy và "chỉnh" một cấu hình hệ thống không thuộc quyền của họ | Cao |
| 2 | Bật / tắt nguồn chỉ là state trong trình duyệt, không gửi lên máy chủ | `useState(PLATFORMS.map(...))` trong `App.tsx`; tìm kiếm luôn gửi `platform: 'all'` (`agentApi.ts`) | Kể cả quản trị viên tắt một sàn thì hệ thống vẫn cào sàn đó; tải lại trang là bật lại tất cả | Cao |
| 3 | Không có API cấu hình nguồn ở máy chủ | Danh sách sàn cố định trong mã | Muốn tắt một sàn đang lỗi phải sửa mã và khởi động lại | Trung bình |
| 4 | Danh sách nguồn có sàn chưa hỗ trợ | `PLATFORMS` | Hiện "5 nền tảng" trong khi thực tế cào 3 (FPT / CellphoneS chưa có) | Trung bình |
| 5 | Màn tra cứu chính sách lọc sàn theo lựa chọn nguồn trong trình duyệt | `PolicyLookupView` nhận `enabledPlatformIds` | Sau khi chuyển cấu hình nguồn cho admin, màn này cần lấy danh sách sàn từ máy chủ | Thấp |
| 6 | Người dùng chưa có màn hình cài đặt; thiếu chế độ giao diện theo giờ và ngôn ngữ tiếng Anh | `useTheme.ts` chỉ có `light` / `dark`, lưu `localStorage`; chuỗi tiếng Việt viết thẳng trong mọi component | Đổi thiết bị phải chọn lại giao diện; người dùng không đọc tiếng Việt không dùng được | Trung bình |
| 7 | Làm ấm kho dùng danh sách từ khóa cố định | `DEFAULT_HOT_CATALOG` trong `batch_crawler.py` | Không theo nhu cầu thật | Thấp |
| 8 | Màn kho dữ liệu không có số liệu chất lượng | `DataWarehousePanel.tsx` | Không thấy số sản phẩm bị guardrails loại, tỉ lệ cào lỗi theo sàn, độ mới RAG | Thấp |

## Đề xuất cải thiện

**A. Cấu hình nguồn & kho dữ liệu — chỉ quản trị viên**

1. **Ẩn với người dùng thường:** mục "Cài đặt nguồn dữ liệu" trên thanh bên và nút "Nguồn dữ liệu" trên thanh tiêu đề chỉ hiện khi `user.role === 'admin'`. Kiểm chứng: đăng nhập tài khoản thường không thấy hai mục này.
2. **Lưu cấu hình ở máy chủ:** bảng `system_settings (key, value_json, updated_by, updated_at)`; API `GET /api/admin/sources` và `PUT /api/admin/sources` (`require_admin`). Mỗi sàn có trạng thái: đang hoạt động / tạm tắt / chưa hỗ trợ.
3. **Áp dụng cho mọi lượt tìm kiếm:** `EcomSearchTool` đọc danh sách sàn đang bật từ cấu hình (mặc định bật cả Tiki, TGDĐ, ĐMX); RAG dùng làm `disabled_platforms`. Kiểm chứng: admin tắt Tiki → lượt tìm tiếp theo của mọi người không còn kết quả Tiki; có test API `403` với người dùng thường.
4. **Danh sách sàn lấy từ máy chủ:** `GET /api/sources` (mọi người dùng, chỉ đọc) trả các sàn đang hoạt động, dùng cho màn tra cứu chính sách và câu chữ "Dữ liệu từ Tiki, TGDĐ, ĐMX" trong giao diện.
5. Ghi lịch sử thay đổi cấu hình (ai đổi, lúc nào) vào nhật ký quản trị.
6. Làm ấm kho theo 10 truy vấn phổ biến 7 ngày qua; thêm số liệu chất lượng vào màn kho dữ liệu (sản phẩm theo sàn, số bị guardrails loại 24 giờ, tỉ lệ cào lỗi, số vector RAG, lần reindex gần nhất).

**B. Cài đặt người dùng — chỉ thiết lập lõi của hệ thống** — ✅ đã làm ngày 30/10/2026 (hộp thoại `PreferencesModal.tsx`, `hooks/usePreferences.tsx`, `src/i18n/`; mục "Cài đặt nguồn dữ liệu" và nút "Nguồn dữ liệu" đã ẩn với người dùng thường)

7. **Hộp thoại "Cài đặt"** cho mọi người dùng, thay chỗ mục "Cài đặt nguồn dữ liệu" trên thanh bên (mục đó chuyển thành của quản trị viên). Chỉ gồm hai nhóm:
   - **Giao diện:** Sáng · Tối · Tự động theo giờ trong ngày (VD tối từ 18:00 đến 6:00, giờ có thể chỉnh). Mở rộng `useTheme` thành `mode: 'light' | 'dark' | 'auto'`, ở chế độ tự động kiểm tra lại mỗi phút. Nút sáng / tối trên thanh tiêu đề giữ làm lối tắt.
   - **Ngôn ngữ:** Tiếng Việt · English. Tách chuỗi giao diện ra tệp `vi.json` / `en.json` (thư viện i18n nhẹ hoặc hook `t()` tự viết); `<html lang>` đổi theo; gửi kèm ngôn ngữ trong yêu cầu chat để trợ lý trả lời đúng ngôn ngữ đã chọn.
8. **Lưu theo tài khoản:** `useSyncedState(userId, 'preferences')` với `{ theme, themeSchedule, language }`, đồng bộ nhiều thiết bị; màn đăng nhập (chưa có tài khoản) dùng giá trị trong trình duyệt.
9. **Không** đưa tùy chọn của từng tính năng (mức giảm theo dõi giá, số sản phẩm đề xuất, hỏi làm rõ…) vào đây — các tùy chọn đó, nếu cần, đặt ngay tại màn hình của tính năng.
10. Kiểm chứng: đổi ngôn ngữ → mọi nhãn trên thanh bên, thanh tiêu đề, hộp thoại đổi theo, không còn chuỗi tiếng Việt sót; chế độ tự động đổi giao diện đúng giờ; đăng nhập thiết bị khác giữ nguyên lựa chọn.

## Liên quan

[04-information-architecture.md — DLG-02, phân quyền màn hình](../04-information-architecture.md), [UC18](../03-use-cases.md), [F04](F04-tim-kiem-thu-thap.md), [F11](F11-tra-cuu-chinh-sach.md), [11-rag.md](../11-rag.md)
