# F07 Săn deal & thẩm định link — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🟡 Săn deal tin hoàn toàn vào giá gốc của sàn
> Mã chính: [`backend/core/agents/deal_finder_agent.py`](../../backend/core/agents/deal_finder_agent.py), [`backend/core/agents/link_parser_agent.py`](../../backend/core/agents/link_parser_agent.py), [`backend/core/tools/url_extractor.py`](../../backend/core/tools/url_extractor.py)

## Đã làm được

- Săn deal: sắp theo mức giảm (`discountPercent`, số tiền tiết kiệm), dùng chung luồng tìm kiếm có nới lỏng.
- Thẩm định link Tiki (API), TGDĐ / ĐMX (JSON-LD, HTML), có thông số và bảo hành; tự nạp vào kho RAG.
- Không đọc được giá hợp lệ → nói rõ, không tạo thẻ sản phẩm (trước đây gán giá giả 100.000 đ).

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | "Deal" = giá gốc − giá bán do sàn công bố | `_saving`, sắp xếp trong `deal_finder_agent.py` | Giá gạch bị đẩy cao (thủ thuật phổ biến) được coi là giảm sâu; không phát hiện "giảm giá ảo" | Cao |
| 2 | Không dùng lịch sử giá đang có | bảng `price_history` | Bỏ phí dữ liệu để nói "đây là giá thấp nhất 30 ngày" | Trung bình |
| 3 | Chưa có voucher / mã giảm giá | — | Giá cuối người dùng trả có thể khác | Thấp |
| 4 | Link rút gọn / link affiliate chưa xử lý (link Shopee / Lazada báo chưa hỗ trợ) | `_extract_generic` | Thẩm định link từ mạng xã hội thường thất bại | Trung bình |
| 5 | Thẩm định link không so với giá nơi khác | `LinkParserAgent.parse` | Chỉ mô tả sản phẩm, chưa trả lời "giá này có tốt không" | Trung bình |

## Đề xuất cải thiện

1. **Kiểm định deal bằng lịch sử:** với sản phẩm có ≥ 3 mốc trong `price_history`, tính giá thấp nhất / trung vị 30 ngày; gắn nhãn "Giá thấp nhất 30 ngày", "Giảm thật so với trung vị X%", hoặc "Giá gốc có thể bị đẩy cao" khi giá bán ≥ trung vị mà sàn vẫn báo giảm sâu.
2. **Thẩm định link có so giá:** sau khi bóc tách, tìm cùng tên sản phẩm trong kho / các sàn khác (dùng RAG + tìm kiếm) và trả lời "rẻ hơn / đắt hơn bao nhiêu so với nơi khác".
3. **Mở link rút gọn** (theo chuyển hướng tới URL cuối, giới hạn 3 bước) trước khi nhận diện sàn.
4. Voucher: để sau, cần nguồn dữ liệu riêng.

## Liên quan

[UC08, UC09](../03-use-cases.md), [BR-011](../requirements/business-rules.md), [F05](F05-xep-hang-noi-long.md), [F10](F10-theo-doi-gia.md)
