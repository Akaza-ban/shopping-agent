# Danh mục tính năng

> Trạng thái: V1 — tất cả tính năng dưới đây đã chạy, trừ các mục ghi rõ "dữ liệu tham khảo" hoặc "tắt mặc định"

Mỗi tính năng ghi màn hình, API và mã nguồn chính. Use case chi tiết: [03-use-cases.md](03-use-cases.md).

## F01 Tài khoản & xác thực

- Đăng ký (email, tên hiển thị, mật khẩu ≥ 8 ký tự, có chữ và số), đăng nhập, đăng xuất, xem / đổi tên hiển thị, đổi mật khẩu.
- Token phiên 30 ngày; đăng xuất và đổi mật khẩu thu hồi phiên ngay. Sai mật khẩu 5 lần liên tiếp bị khóa 5 phút.
- Vai trò `user` / `admin` (email trong `ADMIN_EMAILS` nhận `admin` khi đăng ký).
- **Màn hình:** SCR-01, DLG-04. **API:** `/api/auth/*`. **Mã:** `backend/src/routes/auth.py`, `backend/services/auth/service.py`, `frontend/src/components/AuthView.tsx`.

## F02 Tư vấn mua sắm

- Hội thoại nhiều lượt; router LLM phân loại ý định (`search_products`, `compare_products`, `find_deal`, `parse_link`, `general_advice`, `out_of_scope`) và trích tiêu chí.
- Stream tiến trình, sản phẩm, bảng so sánh, lời tư vấn, câu hỏi gợi ý.
- Ghi chú độ tin cậy: dữ liệu từ kho cũ, tiêu chí đã nới, thông số chưa xác minh.
- **Màn hình:** SCR-03. **API:** `POST /api/chat/stream`, `POST /api/chat`. **Mã:** `backend/core/graph.py`, `backend/core/agents/*`.

## F03 Hỏi làm rõ

- Hỏi ngân sách khi yêu cầu tìm mua không có giá, hãng, model cụ thể; các mức theo ngành hàng + "Không giới hạn ngân sách".
- Mỗi ngành hàng hỏi một lần trong một hội thoại; trạng thái chờ lưu SQLite (còn sau khi khởi động lại).
- **Mã:** `ShopAIAgentWorkflow._maybe_ask_clarification`, `_apply_pending_clarification`.

## F04 Tìm kiếm & thu thập dữ liệu

- Cache-first: SQLite (TTL 2 giờ) → ChromaDB → cào song song TGDĐ, ĐMX, Tiki.
- RAG: embedding đa ngôn ngữ bge-m3 qua API, truy xuất lai vector + BM25 hợp nhất RRF, lọc danh mục đã chuẩn hóa / giá / sàn / độ mới 30 ngày; embedding lỗi thì chỉ tìm từ khóa ([11-rag.md](11-rag.md)).
- Lọc ngữ nghĩa bằng LLM (loại phụ kiện); lọc danh mục Tiki theo mã danh mục.
- Làm giàu từ trang chi tiết (thông số, bảo hành, đổi trả), cache 6 giờ.
- Thu thập hàng loạt các mặt hàng phổ biến (8 từ khóa) khi khởi động nếu dữ liệu cũ hơn 12 giờ, hoặc khi quản trị viên kích hoạt.
- Shopee / Lazada: **đã bỏ** vì cơ chế chống bot.
- **Mã:** `backend/core/tools/ecom_search.py`, `backend/services/catalog/enricher.py`, `backend/services/catalog/batch_crawler.py`, `backend/services/rag/`.

## F05 Xếp hạng & nới lỏng tiêu chí

- Điểm 0–100: khớp thông số 35, ngân sách 20, chất lượng 25, giảm giá 10, sở thích 10 (đổi theo ưu tiên).
- Đánh giá có trọng số Bayes; sản phẩm sai thông số bắt buộc tối đa 55 điểm và có nhãn "Không đúng cấu hình yêu cầu".
- Không có kết quả → bỏ thông số → +20% ngân sách → bỏ hãng. Không có sản phẩm đúng thông số → tìm thêm tới +20% ngân sách.
- **Mã:** `backend/services/catalog/ranker.py`, `ShopAIAgentWorkflow._run_search`.

## F06 So sánh sản phẩm

- Bảng `{columns, rows[{label, values, best_index}]}`: giá, giảm giá, điểm, đánh giá, nơi bán, bảo hành, đổi trả, thông số chung.
- Tự chạy khi có ≥ 2 sản phẩm; so sánh sản phẩm đã lưu không cào lại.
- **API:** sự kiện SSE `comparison`, `POST /api/chat/compare`. **Mã:** `backend/core/tools/spec_comparator.py`, `ComparisonTable.tsx`.

## F07 Săn deal & thẩm định link

- Săn deal: đưa sản phẩm giảm sâu nhất lên đầu, ghi mức tiết kiệm; dùng lại sản phẩm lượt trước khi câu hỏi không nêu sản phẩm.
- Thẩm định link: dán URL sản phẩm vào chat hoặc gọi `POST /api/parse-link`.
- **Mã:** `backend/core/agents/deal_finder_agent.py`, `link_parser_agent.py`.

## F08 Quản lý hội thoại

- Tạo, chuyển, xóa hội thoại; tên = câu hỏi đầu tiên (≤ 80 ký tự); tối đa 30 hội thoại.
- Mỗi hội thoại là một phiên riêng ở máy chủ, thuộc về người tạo.
- **Màn hình:** SCR-03 (cột Hội thoại). **API:** `DELETE /api/chat/history/{session_id}`, `/api/auth/me/data/conversations`.

## F09 Sản phẩm đã lưu

- Lưu / bỏ lưu từ thẻ sản phẩm hoặc bảng so sánh; chọn ≥ 2 sản phẩm để nhờ AI so sánh.
- **Màn hình:** SCR-05. **API:** `/api/auth/me/data/saved-products`.

## F10 Theo dõi giá & lịch sử giá

- Đặt giá mong muốn (gợi ý −5/10/15/20%); kiểm tra định kỳ (mặc định 360 phút) hoặc ngay lập tức.
- Đọc giá thật: JSON-LD trên trang TGDĐ/ĐMX, API chi tiết Tiki. Guardrails (BR-011): giá gốc do server đọc, giá vô lý bị bỏ qua, biến động lớn chờ xác nhận ở lần đọc sau, giảm mạnh tới mức mong muốn thì đọc lại trước khi báo.
- Kết quả tìm kiếm và thẩm định link cũng qua guardrails: loại giá vô lý theo danh mục và giá thấp bất thường so với cùng sản phẩm.
- Biểu đồ lịch sử giá kèm bảng.
- **Màn hình:** SCR-06, DLG-01. **API:** `/api/alerts*`, `GET /api/products/{id}/history`.

## F11 Tra cứu chính sách bảo hành & đổi trả

- So sánh thời hạn đổi trả, điều kiện, phí, hoàn tiền, bảo hành giữa các sàn đã chọn.
- **Dữ liệu tham khảo** (chưa thu thập tự động). Bảo hành / đổi trả trên thẻ sản phẩm thì là dữ liệu thật từ trang chi tiết.
- **Màn hình:** SCR-04.

## F12 Tổng quan, lịch sử hoạt động & tiện ích

- Tổng quan: thao tác nhanh, số lượt tìm kiếm, sản phẩm đề xuất, đã lưu, đang theo dõi giá, nguồn dữ liệu.
- Lịch sử hoạt động theo ngày, lọc theo loại, mở lại kết quả trong chat.
- Góp ý / yêu cầu hỗ trợ (ghi vào lịch sử hoạt động); giao diện sáng / tối; thanh bên thu gọn.
- **Màn hình:** SCR-02, SCR-07, DLG-03.

## F13 Nguồn & kho dữ liệu

- Bật/tắt nguồn trên giao diện; xem số sản phẩm trong kho, lần cập nhật gần nhất.
- Kích hoạt thu thập lại: **chỉ quản trị viên**.
- **Màn hình:** DLG-02. **API:** `/api/crawler/status`, `/api/crawler/trigger`.
