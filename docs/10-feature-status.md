# Bảng đánh dấu tính năng — đã có / một phần / chưa có

> Rà soát theo mã nguồn ngày 29/10/2026 (`backend/`, `frontend/`)
>
> ✅ Đã có và chạy được · 🟡 Có nhưng còn hạn chế · ❌ Chưa có

## 1. Tài khoản & bảo mật

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Đăng ký (kiểm tra email, mật khẩu ≥ 8 ký tự có chữ + số) | ✅ | `POST /api/auth/register` |
| Đăng nhập, giữ phiên khi tải lại trang | ✅ | Token 30 ngày |
| Đăng xuất (thu hồi token ở máy chủ) | ✅ | |
| Đổi tên hiển thị, đổi mật khẩu (đăng xuất thiết bị khác) | ✅ | Hộp thoại Tài khoản |
| Khóa tạm sau 5 lần đăng nhập sai, chống dò email | ✅ | Bộ đếm nằm trong RAM — mất khi khởi động lại |
| Phân quyền người dùng / quản trị viên | ✅ | Quản trị viên theo `ADMIN_EMAILS` |
| Dữ liệu cá nhân đồng bộ theo tài khoản (nhiều thiết bị) | ✅ | Ghi đè nguyên khối, bản sau thắng |
| Quên mật khẩu / đặt lại qua email | ❌ | |
| Xác thực email khi đăng ký | ❌ | |
| Đăng nhập Google / Facebook, xác thực 2 lớp | ❌ | |
| Trang quản trị người dùng (khóa / mở, đổi vai trò) | ❌ | Vai trò chỉ gán lúc đăng ký |
| Giới hạn tần suất gọi API tư vấn theo người dùng | ❌ | Chưa kiểm soát chi phí LLM |

## 2. Tư vấn mua sắm (AI Agent)

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Hiểu yêu cầu bằng ngôn ngữ tự nhiên, trích tiêu chí (LLM) | ✅ | Dự phòng phân loại từ khóa khi LLM lỗi |
| Điều phối bằng LangGraph, stream tiến trình (SSE) | ✅ | |
| Hỏi làm rõ ngân sách, nhớ qua khởi động lại | ✅ | Chỉ hỏi ngân sách, chưa hỏi các tiêu chí khác (mục đích, hãng…) |
| Hội thoại nhiều lượt, hỏi nối tiếp về sản phẩm lượt trước | ✅ | |
| Từ chối câu hỏi ngoài phạm vi mua sắm | ✅ | |
| Chuỗi dự phòng LLM DeepSeek → OpenRouter → Groq | ✅ | Nhà cung cấp không kết nối được bị bỏ qua ngay (kiểm tra TCP, nhớ 1–5 phút) thay vì chờ hết timeout |
| Trò chuyện xã giao tự nhiên | ✅ | LLM phân loại theo ý nghĩa (`smalltalk`) và viết câu trả lời trong cùng lần gọi; không chạy các bước phân tích, không tìm kiếm, theo ngôn ngữ đã chọn |
| Câu trả lời trung thực (không bịa giá, ghi chú độ tin cậy) | ✅ | |
| Gợi ý câu hỏi tiếp theo | ✅ | Sinh theo mẫu, chưa dùng LLM |
| Hiển thị nguồn trích dẫn của từng sản phẩm | ✅ | |
| Tìm bằng hình ảnh / OCR | ❌ | `tests/test_input_ocr.py` là tệp rỗng |
| Nhập bằng giọng nói | ❌ | |

## 3. Thu thập & xử lý dữ liệu sản phẩm

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Tiki (API JSON, lọc theo mã danh mục) | ✅ | |
| Thế Giới Di Động, Điện Máy Xanh (HTML) | 🟡 | Chỉ lấy được ~20 sản phẩm đầu của trang danh mục; tìm từ khóa dài cần JavaScript |
| Shopee, Lazada | Đã bỏ | Bị chặn captcha, API hay đổi nên không cào và không đọc link |
| FPT Shop, CellphoneS | ❌ | Chỉ có trong danh sách sàn của màn tra cứu chính sách |
| Playwright cho trang render bằng JavaScript | ❌ | `des.md` có nhắc nhưng chưa dùng |
| Cache SQLite (2 giờ) → RAG ChromaDB → cào trực tiếp | ✅ | |
| RAG: embedding đa ngôn ngữ bge-m3 qua API | ✅ | OpenRouter, dùng lại `OPENROUTER_API_KEY`; thêm 1,5–5 s mỗi truy vấn mới |
| RAG: truy xuất lai vector + BM25 (RRF), lọc danh mục / giá / sàn | ✅ | Danh mục theo mã của sàn (Tiki, slug TGDĐ / ĐMX), luật tên dự phòng |
| RAG: độ mới (bỏ bản > 30 ngày, sàn tắt), nạp lại kho | ✅ | `scripts/rag/reindex.py` |
| RAG: dự phòng khi embedding API lỗi | ✅ | Chỉ tìm từ khóa, ngưỡng chặt |
| RAG: bộ đánh giá recall@k / MRR | ✅ | 51 truy vấn; recall@5 0,28 → 0,88 ([11-rag.md](11-rag.md)) |
| Bảng mã danh mục Tiki đầy đủ | 🟡 | Mới có các ngành đã gặp; mã lạ dùng luật tên |
| RAG cho câu hỏi mô tả nhu cầu chung ("điện thoại chụp ảnh đẹp") | 🟡 | Thường trả rỗng → cào trực tiếp; chưa có reranker / viết lại truy vấn |
| RAG tra cứu chính sách bảo hành / đổi trả | ❌ | Để sau |
| Lọc phụ kiện / hàng không liên quan bằng LLM | ✅ | |
| Đọc trang chi tiết: thông số, bảo hành, đổi trả | ✅ | Cache 6 giờ |
| Làm ấm kho khi khởi động, thu thập hàng loạt (admin) | ✅ | 8 từ khóa cố định, chưa chỉnh được danh mục từ giao diện |

## 4. Xếp hạng, so sánh, săn deal

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Xếp hạng 0–100 có lý do, đổi trọng số theo ưu tiên | ✅ | |
| Đối chiếu thông số bắt buộc (đúng / sai / chưa rõ) | ✅ | |
| Nới lỏng tiêu chí, tìm thêm tới +20% ngân sách | ✅ | |
| Bảng so sánh trong khung chat | ✅ | |
| Nhờ AI so sánh sản phẩm đã lưu | ✅ | Chỉ dựng bảng + nhận xét, không có lời tư vấn LLM |
| Săn deal (xếp theo mức giảm) | ✅ | Chỉ dựa trên giá gốc / giá bán của sàn, không có voucher |
| Thẩm định link sản phẩm | 🟡 | Tiki, TGDĐ, ĐMX; link Shopee / Lazada báo chưa hỗ trợ |
| Tìm mã giảm giá / voucher | ❌ | |

## 5. Hội thoại & dữ liệu cá nhân

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Tạo / chuyển / xóa hội thoại, tên = câu hỏi đầu tiên | ✅ | Tối đa 30 hội thoại |
| Đổi tên hội thoại, tìm kiếm trong hội thoại | ❌ | |
| Lưu / bỏ lưu sản phẩm, tìm trong danh sách đã lưu | ✅ | |
| Tổng quan (thống kê, gần đây) | ✅ | |
| Lịch sử hoạt động, lọc, mở lại kết quả | ✅ | Tối đa 200 hoạt động |
| Góp ý / yêu cầu hỗ trợ | 🟡 | Chỉ ghi vào lịch sử hoạt động của người gửi, **không gửi tới ai** |
| Xuất dữ liệu / báo cáo (Excel, PDF) | ❌ | |

## 6. Theo dõi giá

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Tạo / xem / bỏ theo dõi, gợi ý mức −5…−20% | ✅ | |
| Đọc giá thật (JSON-LD, API Tiki), guardrails chặn giá bất thường | ✅ | Giá gốc do server đọc; biến động lớn chờ xác nhận ở lần đọc sau; giảm mạnh tới mức mong muốn thì đọc lại trước khi báo |
| Guardrails giá ở bước tìm kiếm / thẩm định link | ✅ | Loại giá vô lý theo danh mục và giá thấp bất thường so với cùng sản phẩm; bỏ giá dự phòng 100.000 đ |
| Biết sản phẩm còn hàng khi kiểm tra giá | ✅ | JSON-LD `availability` (TGDĐ / ĐMX), `inventory_status` (Tiki); hết hàng thì không báo đạt giá, hiện nhãn "Hết hàng" |
| Nhật ký kiểm tra giá lưu bền | ✅ | Bảng `price_checks`; nút "Nhật ký kiểm tra" trên từng yêu cầu |
| Biết còn hàng ở kết quả tìm kiếm | ❌ | Chỉ kiểm tra khi theo dõi giá |
| Kiểm tra định kỳ (mặc định 6 giờ) và "Kiểm tra ngay" | ✅ | Vòng nền chạy trong tiến trình máy chủ |
| Lịch sử giá dạng biểu đồ + bảng | ✅ | Chỉ có mốc khi giá thay đổi lúc hệ thống đọc |
| Báo trong ứng dụng khi đạt giá (huy hiệu, lịch sử hoạt động) | ✅ | Cần mở ứng dụng mới thấy |
| Gửi email / thông báo đẩy khi đạt giá | ❌ | Đã có cột `user_email` chờ dùng |
| Sửa giá mong muốn của yêu cầu đã tạo | ❌ | Phải bỏ theo dõi rồi tạo lại |

## 7. Tra cứu chính sách bảo hành & đổi trả

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Bảo hành / đổi trả **của từng sản phẩm** (thẻ, bảng so sánh) | ✅ | Dữ liệu thật từ trang chi tiết |
| Màn hình so sánh chính sách giữa các sàn | 🟡 | **Dữ liệu tham khảo cố định** trong frontend; các bước tiến trình chỉ mô phỏng |
| Thu thập tự động chính sách từ trang của sàn | ❌ | |

## 8. Giao diện & cấu hình

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Giao diện sáng / tối đồng nhất | ✅ | |
| Thanh bên thu gọn, dùng được trên màn hình hẹp | ✅ | Chưa tối ưu riêng cho điện thoại |
| Hiển thị lời tư vấn dạng Markdown (bảng, danh sách, link) | ✅ | |
| Bật / tắt nguồn dữ liệu (cấu hình của quản trị viên) | 🟡 | Đã ẩn với người dùng thường; vẫn chỉ là state trên trình duyệt: không lưu ở máy chủ, không ảnh hưởng thu thập / tìm kiếm — xem [reviews/F13](reviews/F13-nguon-kho-du-lieu.md) phần A |
| Cài đặt người dùng: giao diện sáng / tối / tự động theo giờ | ✅ | Hộp thoại "Cài đặt", lưu theo tài khoản (`preferences`), dùng được ở màn đăng nhập |
| Xem tình trạng kho dữ liệu | ✅ | |
| Đa ngôn ngữ Tiếng Việt / English | ✅ | Toàn bộ giao diện (`src/i18n/`, kiểm tra bằng `npm run i18n:check`); trợ lý trả lời theo ngôn ngữ đã chọn. Dữ liệu sản phẩm, ghi chú dữ liệu và ghi chú kiểm tra giá từ backend vẫn tiếng Việt |

## 9. API có ở backend nhưng giao diện chưa dùng

| API | Ghi chú |
|---|---|
| `POST /api/chat` (trả một lần) | Giao diện dùng bản stream |
| `GET /api/chat/history/{id}` | Hội thoại lấy từ dữ liệu cá nhân (`user_data`) |
| `GET /api/products/search`, `GET /api/products/{id}` | Tìm qua khung chat |
| `POST /api/parse-link` | Thẩm định link qua khung chat |
| `GET /api/alerts/metrics` | Nhật ký kiểm tra giá toàn hệ thống, chưa có màn hình quản trị |

## 10. Vận hành & chất lượng

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| 147 test tự động (pytest), kiểm thử đầu-cuối trên trình duyệt | ✅ | Vài test phụ thuộc mạng / LLM thật |
| Tài liệu (yêu cầu, arc42, C4, UML, OpenAPI, truy vết) | ✅ | `docs/` |
| Tracing LangSmith | 🟡 | Có cấu hình, bật khi có `LANGCHAIN_API_KEY` |
| Chạy nhiều worker / PostgreSQL / Alembic | ❌ | Hiện một worker, SQLite |
| Docker / CI tự động | ❌ | |
| Dọn token hết hạn, sao lưu CSDL định kỳ | ❌ | |
