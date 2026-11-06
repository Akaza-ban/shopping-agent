# Quy tắc nghiệp vụ — Shopping AI V1

> Trạng thái: V1 — mọi quy tắc dưới đây được thực thi ở backend

## BR-001 — Vai trò

- **Liên quan:** US01–US18; mọi API được bảo vệ.
- **Quy tắc:** Chỉ có hai vai trò `user` và `admin`. Vai trò `admin` chỉ được gán khi đăng ký bằng email nằm trong `ADMIN_EMAILS`. Backend quyết định quyền; giao diện chỉ ẩn nút.

## BR-002 — Quyền sở hữu dữ liệu cá nhân

- **Liên quan:** UC10, UC11, UC12; `chat_sessions`, `price_alerts`, `user_data`.
- **Quy tắc:** Hội thoại, yêu cầu theo dõi giá và dữ liệu cá nhân chỉ chủ sở hữu đọc / ghi. Hội thoại mới gắn với người tạo ở lượt đầu tiên; hội thoại tạo trước khi có tài khoản (không có chủ) được gắn cho người đầu tiên dùng nó.

## BR-003 — Mật khẩu và phiên

- **Liên quan:** UC01–UC04.
- **Quy tắc:** Mật khẩu ≥ 8 ký tự, có chữ và số, ≤ 72 byte; lưu bằng bcrypt. Token phiên ngẫu nhiên 256 bit, sống 30 ngày, DB chỉ lưu SHA-256. Đăng xuất thu hồi token hiện tại; đổi mật khẩu thu hồi mọi token khác.

## BR-004 — Chống dò tài khoản

- **Liên quan:** UC02.
- **Quy tắc:** Sai email và sai mật khẩu trả cùng thông báo và cùng thời gian xử lý (luôn chạy bcrypt). Sai 5 lần liên tiếp cho một email → khóa đăng nhập 5 phút.

## BR-005 — Dữ liệu trung thực

- **Liên quan:** UC05, UC07, UC09; prompt advisor.
- **Quy tắc:** Trợ lý chỉ trình bày giá, thông số có trong dữ liệu đã thu thập. Khi tiêu chí đã bị nới, dữ liệu lấy từ kho cũ, hoặc thông số chưa xác minh, câu trả lời phải nói rõ (`search_notes`). Không tìm thấy thì nói không tìm thấy, không đưa giá, không dùng lại sản phẩm lượt trước.

## BR-006 — Thông số bắt buộc

- **Liên quan:** UC05.
- **Quy tắc:** Thuộc tính ngắn (≤ 3 từ, ≤ 25 ký tự) trong tiêu chí được coi là thông số bắt buộc và đối chiếu với trang chi tiết: `verified` / `mismatch` / `unknown`. Sản phẩm `mismatch` tối đa 55 điểm, có lý do ghi thông số thật. Mô tả tự do (VD "phù hợp gia đình 4 người") không phải thông số bắt buộc.

## BR-007 — Nới lỏng tiêu chí

- **Liên quan:** UC05.
- **Quy tắc:** Không có kết quả → nới lần lượt, cộng dồn: bỏ thông số → ngân sách +20% → bỏ hãng; dừng ở bước đầu tiên có kết quả và ghi lại đã nới gì. Có kết quả nhưng không sản phẩm nào đúng hết thông số → tìm thêm tới ngân sách +20% (giữ thông số), sản phẩm vượt ngân sách ghi rõ lý do.

## BR-008 — Hỏi làm rõ

- **Liên quan:** UC06.
- **Quy tắc:** Chỉ hỏi khi ý định là tìm mua và không có giá, hãng, model (tên chứa số). Mỗi ngành hàng hỏi tối đa một lần trong một hội thoại. Câu trả lời ở lượt sau được gộp vào tiêu chí đang chờ; chuyển ngành hàng thì bỏ tiêu chí đang chờ.

## BR-009 — Phụ kiện và hàng không liên quan

- **Liên quan:** UC05.
- **Quy tắc:** Sản phẩm là phụ kiện khi người dùng tìm thiết bị chính bị loại (lọc ngữ nghĩa bằng LLM + lọc mã danh mục Tiki). Không loại sản phẩm chỉ vì tên thiếu thông số.

## BR-010 — Theo dõi giá

- **Liên quan:** UC12, UC17.
- **Quy tắc:** Giá gốc của yêu cầu do **server** xác định: đọc trực tiếp từ sàn, không được thì dùng giá đã lưu nếu qua guardrails; không có giá hợp lệ → `400`. Không dùng giá giao diện gửi lên. Giá mong muốn phải > 0 và < giá gốc đó. Giá kiểm tra đọc trực tiếp từ trang sản phẩm. Đạt giá khi giá ≤ giá mong muốn **và** qua guardrails (BR-011). Đạt giá rồi thì không kiểm tra tiếp.

## BR-011 — Guardrails giá

- **Liên quan:** UC05, UC08, UC12, UC17. **Mã:** `backend/services/pricing/guardrails.py`.
- **Quy tắc:**
  1. **Giá hợp lý:** ≥ 10.000 đ và ≤ 500 triệu; laptop ≥ 2 triệu, điện thoại ≥ 500.000 đ. Danh mục lấy theo mã sàn / tên sản phẩm, không theo nhãn gắn theo câu hỏi tìm kiếm.
  2. **Kết quả tìm kiếm / thẩm định link:** loại sản phẩm vi phạm (1) hoặc có giá thấp hơn 25% trung vị giá của các bản ghi cùng sản phẩm (đọc nhầm giá trả góp, phụ kiện). Câu trả lời ghi chú số sản phẩm bị loại. Thẩm định link không đọc được giá hợp lệ thì **không** gán giá dự phòng và không tạo thẻ sản phẩm.
  3. **Kiểm tra giá định kỳ:**
     - Lần đọc vi phạm (1) → bỏ qua, ghi lý do vào `last_note`.
     - Sàn báo **hết hàng** (JSON-LD `availability` của TGDĐ / ĐMX, `inventory_status` của Tiki) → không báo đạt giá, không ghi mốc lịch sử; lưu `in_stock = false` để giao diện hiện nhãn "Hết hàng".
     - Giảm > 75% hoặc tăng > 200% so với mốc trước → **chờ xác nhận** (`pending_price`): chưa ghi lịch sử, chưa báo. Lần kiểm tra sau đọc ra cùng mức (±2%) thì chấp nhận làm mốc mới.
     - Giá ≤ mức mong muốn mà giảm > 30% so với mốc trước → **đọc lại ngay** một lần; khớp (±2%) mới báo đạt giá, không khớp thì chuyển sang chờ xác nhận.
  4. **Nhật ký:** mỗi lần kiểm tra ghi một dòng vào bảng `price_checks` (giá đọc được, còn hàng, kết quả, lý do, độ trễ); giữ 100 lần gần nhất mỗi yêu cầu, xóa theo khi bỏ theo dõi. Chủ yêu cầu xem nhật ký của mình, quản trị viên xem toàn hệ thống.

## BR-012 — Lịch sử giá

- **Liên quan:** UC13.
- **Quy tắc:** Chỉ ghi mốc mới khi giá thay đổi ≥ 1 đ. Giá do giao diện gửi lên khi tạo theo dõi không được ghi vào lịch sử của sản phẩm đã có trong kho.

## BR-013 — Thu thập dữ liệu

- **Liên quan:** UC16.
- **Quy tắc:** Chỉ quản trị viên kích hoạt thu thập hàng loạt. Khi khởi động, chỉ làm ấm kho nếu sản phẩm mới nhất cũ hơn 12 giờ. Shopee / Lazada đã bỏ; người dùng chỉ hỏi các sàn này thì tìm ở các sàn đang hỗ trợ và ghi chú, link của hai sàn báo chưa hỗ trợ.

## BR-014 — Dữ liệu cá nhân trên máy chủ

- **Liên quan:** UC10, UC11, UC15.
- **Quy tắc:** Chỉ bốn khóa được phép; mỗi khóa ≤ 2 MB. Dữ liệu dùng trước khi có tài khoản được chuyển vào tài khoản ở lần đăng nhập đầu tiên rồi xóa bản cũ trên trình duyệt.
