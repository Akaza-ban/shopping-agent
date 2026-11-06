# Tiêu chí nghiệm thu — Shopping AI V1

> Trạng thái: V1 — mỗi tiêu chí ghi bằng chứng kiểm chứng (test tự động trong `backend/tests/` hoặc kiểm thử đầu-cuối E2E)

Ký hiệu bằng chứng: `tên_file::tên_test`; **E2E** = kiểm thử trên trình duyệt với backend thật (xem [09-implementation-status.md](09-implementation-status.md)).

## AC-UC01 — Đăng ký

- Dữ liệu hợp lệ → `201`, trả token và hồ sơ (không có mật khẩu); email chuẩn hóa chữ thường.
- Email sai định dạng, tên < 2 ký tự, mật khẩu < 8 ký tự hoặc thiếu chữ/số → `422` kèm lý do; giao diện báo lỗi ngay tại ô.
- Email đã đăng ký (không phân biệt hoa thường) → `409`.
- Email thuộc `ADMIN_EMAILS` nhận vai trò `admin`.
- **Bằng chứng:** `test_auth::test_register_login_me_logout`, `test_register_validation_and_duplicate`, `test_admin_only_crawler_trigger`; E2E bước 2–3.

## AC-UC02 — Đăng nhập

- Đúng thông tin → `200`, token + hồ sơ; sai email và sai mật khẩu trả **cùng** thông báo `401`.
- Sai 5 lần liên tiếp → `429` trong 5 phút.
- Tải lại trang giữ phiên.
- **Bằng chứng:** `test_auth::test_wrong_password_same_message_and_lockout`; E2E bước 7, 10.

## AC-UC03 — Đăng xuất

- `POST /api/auth/logout` thu hồi token: gọi lại `/api/auth/me` bằng token đó → `401`.
- Giao diện quay về màn đăng nhập và xóa token khỏi trình duyệt.
- **Bằng chứng:** `test_auth::test_register_login_me_logout`; E2E bước 6.

## AC-UC04 — Quản lý tài khoản

- Sai mật khẩu hiện tại → `400`; mật khẩu mới yếu → `422`.
- Đổi mật khẩu thành công: phiên hiện tại vẫn dùng được, phiên khác → `401`, đăng nhập bằng mật khẩu mới được.
- **Bằng chứng:** `test_auth::test_change_password_revokes_other_sessions`.

## AC-UC05 — Tư vấn mua sắm

- API riêng tư không có token → `401`.
- Sự kiện stream theo thứ tự `status → products → comparison → token → suggestions → done`.
- `ainvoke` và `astream` dùng chung một đồ thị, cho cùng kết quả.
- Tham số `platform` được áp vào tiêu chí trước khi tìm.
- Sản phẩm sai thông số bắt buộc xếp sau và có lý do chứa thông số thật.
- Tìm không có kết quả: không dùng lại sản phẩm lượt trước, không đưa giá.
- Sản phẩm thiếu đánh giá có `rating = 0`, không hiển thị 5 sao.
- Cụm ngân sách không lọt vào từ khóa gửi sàn.
- **Bằng chứng:** `test_auth::test_private_apis_require_login`; `test_architecture_level3::test_stream_event_order_for_search`, `test_execute_and_stream_share_graph`, `test_platform_filter_applied_before_search`; `test_advisor_level2::test_rank_verified_beats_unknown_beats_mismatch`, `test_crawler_query_drops_budget_phrases`; `test_search_level1::test_advisor_reports_no_products_instead_of_reusing_old_ones`, `test_missing_rating_is_not_five_stars`.

## AC-UC06 — Trả lời câu hỏi làm rõ

- Yêu cầu chung chung (không giá, hãng, model) → hỏi ngân sách, không cào sàn; yêu cầu cụ thể → không hỏi.
- Câu trả lời ở lượt sau được gộp vào tiêu chí đang chờ; cùng ngành hàng không hỏi lại.
- Trạng thái chờ còn sau khi khởi động lại máy chủ.
- **Bằng chứng:** `test_advisor_level2::test_clarification_asked_once_and_answer_merged`, `test_no_clarification_when_query_is_specific`; `test_architecture_level3::test_pending_clarification_survives_restart`.

## AC-UC07 — So sánh sản phẩm

- Bảng có hàng giá, giảm giá, điểm, đánh giá, nơi bán, bảo hành, đổi trả và thông số chung; `best_index` đúng (giá thấp nhất, điểm cao nhất, RAM lớn nhất…).
- `POST /api/chat/compare` dựng bảng từ sản phẩm gửi lên, không cào lại.
- **Bằng chứng:** `test_advisor_level2::test_comparison_table_marks_best_cells`; `test_architecture_level3::test_compare_endpoint_builds_table`.

## AC-UC08 — Thẩm định link

- URL trong câu hỏi được nhận dạng ý định `parse_link`.
- **Bằng chứng:** `test_agents::test_link_parser_intent`.

## AC-UC09 — Săn deal

- Sản phẩm xếp theo mức giảm, ghi chú số tiền tiết kiệm; không nêu sản phẩm thì dùng lại sản phẩm lượt trước, không cào lại.
- **Bằng chứng:** `test_architecture_level3::test_deal_finder_orders_by_discount_and_notes`, `test_deal_node_reuses_previous_products`.

## AC-UC10 — Quản lý hội thoại

- Xóa hội thoại xóa tin nhắn, ngữ cảnh, trạng thái làm rõ ở RAM và SQLite.
- Người khác đọc / xóa hội thoại → `403`.
- **Bằng chứng:** `test_architecture_level3::test_delete_conversation_clears_memory_and_db`; `test_auth::test_conversations_are_private`.

## AC-UC11 — Lưu sản phẩm & dữ liệu cá nhân

- Dữ liệu cá nhân chỉ chủ tài khoản đọc được; khóa không hợp lệ → `404`.
- Xóa dữ liệu trên trình duyệt rồi đăng nhập lại vẫn thấy dữ liệu từ máy chủ; tài khoản khác không thấy.
- **Bằng chứng:** `test_auth::test_user_data_sync`; E2E bước 8–9.

## AC-UC12 — Theo dõi giá

- Giá mong muốn ≥ giá hiện tại → `400`.
- Tạo yêu cầu: giá gốc do server đọc từ sàn, không dùng giá client gửi; mức mong muốn ≥ giá đó → `400` kèm giá hiện tại.
- Kiểm tra giá: đạt giá → `triggered` và ghi mốc lịch sử; chưa đạt → `watching`, cập nhật giá thấp nhất; không đọc được giá → ghi chú, giữ trạng thái.
- Giảm > 75% / tăng > 200% → chờ xác nhận (`pendingPrice`), lần đọc sau khớp ±2% thì chấp nhận; giảm > 30% tới mức mong muốn → đọc lại, khớp mới báo; giá vô lý (laptop 100.000 đ) → bỏ qua.
- Sàn báo hết hàng → không báo đạt giá, `inStock = false`, nhãn "Hết hàng"; còn hàng trở lại và giá ≤ mục tiêu → báo đạt giá.
- Mỗi lần kiểm tra có một dòng trong nhật ký (`GET /alerts/{id}/checks`); người khác xem nhật ký → `404`.
- Người khác không thấy / không xóa được (`404`).
- **Bằng chứng:** `test_price_alerts::test_watcher_triggers_and_records_history`, `test_watcher_handles_unreadable_price`, `test_parse_mwg_price_from_json_ld`; `test_auth::test_price_alerts_are_private`.

## AC-UC13 — Lịch sử giá

- Trả các mốc giá theo thời gian tăng dần; mốc chỉ thêm khi giá thay đổi.
- **Bằng chứng:** `test_cache_first_search::test_product_price_history_api`; `test_product_repository::test_upsert_price_change_tracking`.

## AC-UC14 — Tra cứu chính sách

- Hiển thị bảng so sánh cho các sàn đã chọn, nêu sàn có thời hạn đổi trả dài nhất. **Dữ liệu tham khảo** — không có test tự động.

## AC-UC15 — Tổng quan & lịch sử hoạt động

- Thống kê lấy từ dữ liệu của tài khoản; hoạt động lọc được theo loại, mở lại trong chat. Kiểm chứng thủ công / E2E.

## AC-UC16 — Nguồn & kho dữ liệu

- Người dùng thường gọi `POST /api/crawler/trigger` → `403`; quản trị viên được.
- Làm ấm kho chỉ khi dữ liệu cũ hơn 12 giờ.
- **Bằng chứng:** `test_auth::test_admin_only_crawler_trigger`; `test_batch_crawler::test_should_warmup_logic`, `test_crawler_trigger_api_background`.

## AC-UC17 — Kiểm tra giá định kỳ

- Vòng nền chạy theo `PRICE_WATCH_INTERVAL_MINUTES`, lần đầu sau một chu kỳ; logic kiểm tra như AC-UC12.
- Bảng `price_alerts` cũ được tự bổ sung cột mới.
- **Bằng chứng:** `test_price_alerts::test_init_db_adds_new_alert_columns`; logic dùng chung với AC-UC12.

## AC-UC18 — Góp ý / hỗ trợ

- Nội dung được ghi vào lịch sử hoạt động của tài khoản. **Bằng chứng:** E2E bước 4 và 8.

## Định nghĩa Hoàn thành (Definition of Done)

Một tính năng được coi là xong khi:

1. Có test tự động cho quy tắc nghiệp vụ và quyền truy cập (hoặc E2E nếu là hành vi thuần giao diện).
2. `pytest` (thư mục `backend/tests`) đạt; frontend qua `tsc --noEmit` và `vite build`.
3. API có trong [openapi.json](api/openapi.json); tài liệu use case / tiêu chí được cập nhật.
4. Lỗi trả về có `detail` tiếng Việt người dùng đọc được.
