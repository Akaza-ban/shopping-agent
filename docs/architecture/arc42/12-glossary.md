# 12. Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| AI Agent | Hệ thống dùng LLM để hiểu yêu cầu và gọi công cụ (tìm kiếm, so sánh…) thay vì chỉ trả lời văn bản |
| LangGraph / StateGraph | Thư viện dựng luồng agent dạng đồ thị trạng thái; mỗi node đọc / ghi `AgentState` |
| `AgentState` | Trạng thái một lượt tư vấn: câu hỏi, ý định, tiêu chí, sản phẩm, bảng so sánh, câu hỏi làm rõ, ghi chú, câu trả lời |
| Ý định (intent) | `search_products`, `compare_products`, `find_deal`, `parse_link`, `general_advice`, `out_of_scope` |
| Tiêu chí (`UniversalSearchCriteria`) | Danh mục, khoảng giá, hãng, thuộc tính, mục đích, ưu tiên, từ khóa đã làm sạch |
| Thông số bắt buộc | Thuộc tính ngắn trong tiêu chí (VD `gpu: RTX 4070`) được đối chiếu với trang chi tiết |
| `verified` / `mismatch` / `unknown` | Kết quả đối chiếu: đúng / sai / chưa xác minh được |
| Nới lỏng tiêu chí (relaxation) | Bỏ dần thông số, nới ngân sách, bỏ hãng khi không có kết quả |
| Tìm thêm (upsell search) | Tìm tới +20% ngân sách khi không sản phẩm nào đúng thông số |
| Hỏi làm rõ (clarification) | Câu hỏi ngân sách khi yêu cầu còn chung |
| Làm giàu (enrichment) | Đọc trang chi tiết để bổ sung thông số, bảo hành, đổi trả |
| Lọc ngữ nghĩa | LLM xác định sản phẩm là thiết bị chính hay phụ kiện / không liên quan |
| RAG | Tìm sản phẩm đã thu thập trong ChromaDB theo độ tương đồng ngữ nghĩa + từ khóa, trước khi cào trực tiếp |
| bge-m3 | Mô hình embedding đa ngôn ngữ của BAAI (1024 chiều), gọi qua OpenRouter |
| BM25 | Thuật toán xếp hạng theo từ khóa (tần suất từ, độ hiếm, độ dài tài liệu) |
| RRF | Reciprocal Rank Fusion: cộng `1 / (k + hạng)` để hợp nhất nhiều danh sách xếp hạng |
| Cache-first | Tra kho trước, chỉ cào sàn khi cần |
| `search_notes` | Ghi chú độ tin cậy gửi kèm kết quả (dữ liệu cũ, đã nới, chưa xác minh…) |
| SSE | Server-Sent Events: máy chủ đẩy chuỗi sự kiện qua một kết nối HTTP |
| Guardrails | Luật kiểm định giá (`services/pricing/guardrails.py`): giá hợp lý theo danh mục, giá thấp bất thường so với cùng sản phẩm, biến động lớn cần xác nhận, đọc lại trước khi báo đạt giá |
| JSON-LD | Dữ liệu có cấu trúc (schema.org `Product/Offer`) nhúng trong trang, dùng để đọc giá |
| TGDĐ / ĐMX | Thế Giới Di Động / Điện Máy Xanh |
| MWG | Mobile World Group — tập đoàn sở hữu TGDĐ và ĐMX (dùng trong tên hàm `parse_mwg_*`) |
| Làm ấm kho (warm-up) | Thu thập các mặt hàng phổ biến khi khởi động nếu dữ liệu cũ > 12 giờ |
| Dữ liệu cá nhân (`user_data`) | Hội thoại, đã lưu, lịch sử, tìm kiếm gần đây lưu theo tài khoản |
