# F04 Tìm kiếm & thu thập dữ liệu — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🔴 Ưu tiên — chất lượng dữ liệu quyết định chất lượng tư vấn
> Mã chính: [`backend/core/tools/ecom_search.py`](../../backend/core/tools/ecom_search.py), [`backend/services/catalog/enricher.py`](../../backend/services/catalog/enricher.py), [`backend/services/catalog/semantic_filter.py`](../../backend/services/catalog/semantic_filter.py), [`backend/services/rag/`](../../backend/services/rag/), [`backend/services/pricing/guardrails.py`](../../backend/services/pricing/guardrails.py)

## Đã làm được

- Cache-first: SQLite (2 giờ) → RAG (bge-m3 + BM25) → cào song song Tiki, TGDĐ, ĐMX.
- Lọc phụ kiện bằng LLM; Tiki lọc theo mã danh mục; danh mục theo mã của sàn.
- Làm giàu từ trang chi tiết (thông số, bảo hành, đổi trả), cache 6 giờ.
- Guardrails giá: loại giá vô lý và giá thấp bất thường trước khi hiển thị / lưu; bỏ giá dự phòng 100.000 đ khi thẩm định link.
- RAG có bộ đánh giá: recall@5 0,28 → 0,88 ([11-rag.md](../11-rag.md)).

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Trang danh mục TGDĐ / ĐMX chỉ đọc được ~20 sản phẩm đầu; tìm từ khóa dài cần JavaScript | Bộ phân tích HTML MWG trong `ecom_search.py` | Bỏ sót mẫu phù hợp, nhất là khi lọc theo ngân sách / cấu hình | Cao |
| 2 | Đã bỏ Shopee / Lazada (captcha) | — | Thiếu hai nguồn lớn nhất → so sánh giá chưa đầy đủ | Cao |
| 3 | Cache tìm kiếm khớp chính xác chuỗi từ khóa | `get_cached_search` (so `query.lower().strip()`) | "laptop gaming" và "laptop chơi game" là hai lần cào riêng | Trung bình |
| 4 | Cache trang chi tiết nằm trong RAM | `DETAIL_CACHE_TTL_SECONDS`, dict trong `product_enricher.py` | Khởi động lại mất cache; nhiều worker cào trùng | Thấp |
| 5 | Kết quả tìm kiếm không biết còn hàng | Chỉ Price Watcher đọc `availability` | Có thể đề xuất sản phẩm đang hết hàng | Trung bình |
| 6 | Hai giá mâu thuẫn cùng sản phẩm lệch < 4 lần không xử lý được | `screen_products` chỉ loại giá *thấp* bất thường | VD Casper 7.5 kg: 3,79 tr và 13,79 tr cùng tồn tại | Thấp |
| 7 | Mỗi truy vấn RAG mới tốn 1,5–5 s gọi embedding API | `services/rag/embeddings.py` | Tăng độ trễ khi kho có kết quả | Thấp |
| 8 | Bộ lọc ngữ nghĩa gọi LLM ở mọi nguồn, kể cả cache đã lọc | `semantic_filter.filter_products` trong `run()` | Tốn một lượt gọi LLM / lượt tìm | Thấp |

## Đề xuất cải thiện

1. **Playwright cho TGDĐ / ĐMX** (chỉ khi trang danh sách trả < N sản phẩm hoặc từ khóa dài): cuộn / bấm "Xem thêm" để lấy đủ danh sách; giới hạn đồng thời 2 trang. Kiểm chứng: fixture "laptop gaming" lấy được > 20 sản phẩm.
2. **Nguồn bù cho Shopee / Lazada đã bỏ:** API đối tác / affiliate nếu có; trước mắt bổ sung FPT Shop, CellphoneS (HTML ổn định hơn).
3. **Cache theo truy vấn đã chuẩn hóa:** khóa cache = (danh mục, thực thể chính, khoảng giá) từ router thay vì chuỗi gốc; hoặc tra RAG trước khi coi là cache miss (đã làm một phần).
4. **Đọc còn hàng ở bước làm giàu:** `product_enricher.enrich` đã tải trang chi tiết — đọc thêm `availability` / `inventory_status` (dùng lại `parse_mwg_availability`), gắn nhãn và hạ hạng sản phẩm hết hàng.
5. **Giải quyết giá mâu thuẫn:** khi cùng sản phẩm có hai giá lệch > 2 lần, ưu tiên bản ghi mới nhất từ trang chi tiết; ghi chú "giá chưa thống nhất giữa các lần thu thập".
6. Cache trang chi tiết và cache embedding truy vấn vào SQLite.

## Liên quan

[11-rag.md](../11-rag.md), [BR-011](../requirements/business-rules.md), [ADR-004, ADR-005, ADR-013](../architecture/arc42/09-architecture-decisions.md), [arc42 §11 TD-01, TD-02](../architecture/arc42/11-risks-and-technical-debt.md)
