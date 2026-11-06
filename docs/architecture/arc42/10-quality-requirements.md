# 10. Yêu cầu chất lượng

Danh sách đầy đủ: [non-functional-requirements.md](../../requirements/non-functional-requirements.md). Dưới đây là các kịch bản chất lượng then chốt.

## QR-01 Trung thực dữ liệu

| Nguồn kích thích | Kích thích | Phản hồi | Thước đo |
|---|---|---|---|
| Người dùng | Hỏi laptop có RTX 4070, các sàn chỉ có máy RTX 3050 | Không trình bày máy RTX 3050 như phù hợp; gắn nhãn sai cấu hình, ghi thông số thật, tìm thêm +20% ngân sách và báo kết quả | `test_rank_verified_beats_unknown_beats_mismatch`; thử thật với RTX 4050 |

## QR-02 Riêng tư

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Người dùng B gọi API với id hội thoại / yêu cầu theo dõi của A | `403` / `404`, không lộ dữ liệu | `test_conversations_are_private`, `test_price_alerts_are_private` |

## QR-03 Chống dò tài khoản

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Thử nhiều mật khẩu / email | Cùng thông báo, cùng thời gian; khóa 5 phút sau 5 lần sai | `test_wrong_password_same_message_and_lockout` |

## QR-04 Phản hồi minh bạch

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Gửi câu hỏi cần cào mới | Sự kiện `status` đầu tiên ngay; sản phẩm hiện trước lời tư vấn | `test_stream_event_order_for_search`; đo thực tế 14–22 s cả lượt |

## QR-05 Bền vững trước lỗi LLM

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Nhà cung cấp LLM chính lỗi | Chuyển nhà cung cấp kế; tất cả lỗi → câu trả lời dựng sẵn | `test_step4_zero_crash_fallback_on_error` |

## QR-06 Không báo nhầm giá

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Đọc được giá giảm 92% (lỗi trang / phụ kiện) | Bỏ qua, giữ giá cũ, ghi lý do | `test_watcher_triggers_and_records_history` |

## QR-07 Phục hồi sau khởi động lại

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Máy chủ khởi động lại giữa lúc chờ câu trả lời làm rõ | Câu trả lời vẫn được gộp đúng | `test_pending_clarification_survives_restart` |

## QR-08 Bảo trì bộ thu thập

| Kích thích | Phản hồi | Thước đo |
|---|---|---|
| Sàn đổi tên class CSS | Bộ phân tích dựa trên cấu trúc vẫn đọc được; test fixture phát hiện thay đổi lớn | `test_parse_tgdd_listing_2026`, `test_parse_dmx_listing_2026`, `test_live_tgdd_layout_still_parsable` |
