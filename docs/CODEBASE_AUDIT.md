# Đánh giá chất lượng và khả năng bảo trì của mã nguồn

> Ngày đánh giá: 09/11/2026. Phạm vi: `backend/` (FastAPI + LangGraph) và `frontend/` (React + Vite).
> Tài liệu này chỉ **nhận định và đề xuất**. Chưa có dòng code nào được sửa theo nó.

---

## 0. Phạm vi và giới hạn

**Đã làm**
- Đọc cấu trúc thư mục, quy tắc phân tầng trong `backend/README.md` và cấu hình `backend/pyproject.toml`.
- Đọc trực tiếp các file chính:
  - Backend: `src/`, `application/`, `core/graph.py`, `core/flows/`, `core/tools/`, `integrations/platforms/`, `integrations/llm/client.py`, `database/repositories/`, `memory/session_manager.py`, `jobs/price_watcher.py`, `services/catalog/{ranker,data_processor}.py`.
  - Frontend: `App.tsx`, `SearchAssistantView.tsx`, `SavedProductsView.tsx`, `services/agentApi.ts`, `services/shoppingService.ts`, `i18n/`.
- Chạy công cụ:
  - `ruff check` / `ruff format --check` cho backend: sạch tại thời điểm đánh giá.
  - `tsc --noEmit --noUnusedLocals` cho frontend: sạch.
  - Một script AST đo số dòng và số nhánh (if/for/try/bool-op/comprehension) của từng hàm Python.
  - `grep` để tìm các import đi sai hướng giữa các tầng, các singleton và các đoạn code lặp lại.
- Bộ test backend hiện có: `pytest tests/unit tests/integration` cho 250 passed, 4 skipped.

**Chưa làm hoặc chỉ đọc lướt**, nên các nhận định dưới đây không bao phủ những phần này:
- Nội dung các prompt LLM trong `core/prompts/`. Mình không đánh giá chất lượng prompt.
- JSX chi tiết của các view phụ: `DashboardView`, `ActivityLogView`, `FeedbackInboxView`, `AuthView`, `policy/*`. Mới chỉ grep, chưa đọc từng dòng.
- `backend/scripts/` và `docs/` (chỉ kiểm việc tài liệu còn khớp với code hay không).
- Chưa chạy profiling hiệu năng lúc app chạy thật, chưa đo test coverage.

---

## 1. Đánh giá tổng quan

### Backend: khá tốt, nợ kỹ thuật tập trung ở kiểu dữ liệu và vài chỗ phụ thuộc chéo

**Điểm mạnh**
- Phân tầng rõ ràng (`src → application → core → services → integrations/database → shared`), có ghi trong README kèm bảng "Muốn sửa... | Vào".
- Có tầng exception thống nhất (`shared/exceptions.py`). Lỗi của thư viện bên ngoài được đổi sang lỗi riêng của dự án ngay ở biên hệ thống (`integrations/llm`, `database/errors.py`, `integrations/platforms/errors.py`). Route mỏng, chỉ làm một việc.
- Mỗi sàn là một adapter riêng (`integrations/platforms/base.py`): thêm sàn mới không phải sửa luồng tìm kiếm.
- Lint và format theo ruff đều sạch; bộ test rộng (unit + integration).

**Điểm yếu**
- Sản phẩm đi qua mọi tầng dưới dạng `dict[str, Any]` khóa camelCase, nên không có kiểm tra kiểu và rất dễ gõ sai tên khóa.
- Một số import đi ngược chiều phân tầng.
- Singleton cấp module ở khắp nơi, nên test phải monkeypatch.
- Câu tiếng Việt bị viết cứng trong dữ liệu trả về, làm frontend phải dịch lại bằng regex.

### Frontend: chạy được và gọn, nhưng state và trách nhiệm dồn vào vài file lớn, không có test

**Điểm mạnh**
- Không dùng `dangerouslySetInnerHTML` (`Markdown.tsx` tự dựng phần tử React).
- i18n có công cụ kiểm tra (`npm run i18n:check`).
- Hook đồng bộ dữ liệu tách riêng (`useSyncedState`, `usePersistentState`).

**Điểm yếu**
- `SearchAssistantView.tsx` (676 dòng) và `App.tsx` (363 dòng) mỗi file ôm nhiều trách nhiệm.
- `services/agentApi.ts` (413 dòng) trộn HTTP, chuyển đổi dữ liệu, SSE và mọi endpoint.
- Frontend tự đoán lại dữ liệu mà backend đã có sẵn (hãng, ưu/nhược điểm).
- Không có test nào, không có linter/formatter ngoài `tsc`.

---

## 2. Danh sách vấn đề

Mức ưu tiên: **Critical** = gây lỗi hoặc cản trở mọi thay đổi; **High** = làm chậm hoặc gây lỗi thường xuyên khi sửa; **Medium** = khó đọc nhưng còn khoanh vùng được; **Low** = thẩm mỹ, nhất quán.
Rủi ro = khả năng làm thay đổi hành vi hiện tại nếu refactor.

### A. Phân tầng và phụ thuộc chéo (backend)

#### A1. Tầng `integrations` import ngược lên `core` và `services`
- **Vị trí**:
  - `integrations/platforms/base.py:6`, `common.py:7`, `tiki.py:9` import `core.state.UniversalSearchCriteria`;
  - `integrations/platforms/fpt.py:19`, `mwg.py:26` import `services.catalog.reviews.sold_label`.
- **Vấn đề**: README quy định import một chiều `core → services → integrations`, nhưng adapter của từng sàn lại phụ thuộc vào model của agent (`core.state`) và vào nghiệp vụ (`services`).
- **Vì sao khó bảo trì**: đổi một trường của `UniversalSearchCriteria` (vốn là tiêu chí do LLM trích xuất) có thể làm hỏng parser của sàn. Thêm một trường vào `core.state` cũng có thể sinh vòng import.
- **Đề xuất**:
  - Chuyển `sold_label` (hàm thuần định dạng "Đã bán 2,4k") vào `shared/`.
  - Adapter chỉ cần vài trường của tiêu chí (từ khóa, giá tối đa, hãng). Định nghĩa một `SearchQuery` nhỏ trong `shared/` hoặc `integrations/`, và để `core` tạo nó từ `UniversalSearchCriteria`.
- **Ưu tiên**: High. **Rủi ro**: Thấp, chỉ chuyển chỗ và đổi kiểu tham số; test của từng sàn sẽ bắt được lỗi.

#### A2. Repository chứa nghiệp vụ và gọi sang integrations
- **Vị trí**: `database/repositories/product_repo.py:9,12`. Repository gọi `categorize(item)` khi tạo hoặc cập nhật (dòng 93, 129) và `get_platform(...)` khi đổi model sang dict (dòng 24).
- **Vấn đề**: tầng lưu trữ tự quyết định ngành hàng của sản phẩm. Code có chú thích là "ngoại lệ có chủ đích", nhưng vẫn là phụ thuộc chéo.
- **Vì sao khó bảo trì**: muốn đổi luật phân loại thì phải nhớ rằng repository cũng phân loại. Test repository phải kéo theo cả bộ phân loại.
- **Đề xuất**: nơi gọi (`search_sources.remember`, `application/alerts`, `jobs/price_watcher`) tính `category` trước rồi truyền vào; repository chỉ lưu. Thông tin hiển thị của sàn (màu badge) nên ghép ở tầng trả API, không ghép trong `product_model_to_dict`.
- **Ưu tiên**: Medium. **Rủi ro**: Trung bình, vì có nhiều nơi gọi `upsert_products`; bỏ sót một nơi thì sản phẩm mất ngành hàng.

#### A3. Use case gọi thẳng vào job chạy nền
- **Vị trí**: `application/alerts.py:12` (`from jobs.price_watcher import price_watcher_service`); `application/crawler.py:9` (`from jobs.batch_crawler import ...`).
- **Vấn đề**: `create_alert` và `check_now` mượn object của job nền để đọc giá và kiểm tra ngay. README đặt `jobs` ngang hàng với `src` (đều là điểm vào), không phải tầng dưới của `application`.
- **Vì sao khó bảo trì**: `price_watcher_service` vừa là vòng lặp nền, vừa giữ `asyncio.Lock`, vừa là service đọc giá. Người dùng bấm "kiểm tra ngay" phải chờ lock của đợt quét nền.
- **Đề xuất**: tách phần "đọc giá và đánh giá một yêu cầu theo dõi" (`_read`, `_evaluate`, `_check_one`) thành một service trong `services/pricing/`. Job nền và `application/alerts.py` cùng gọi service đó.
- **Ưu tiên**: Medium. **Rủi ro**: Trung bình, vì phải giữ nguyên thứ tự kiểm tra lại giá (`_confirm_drop`) và ghi nhật ký. Đã có test trong `tests/integration/test_price_alerts.py`.

#### A4. Singleton cấp module, phụ thuộc ẩn
- **Vị trí**: 21 instance cấp module như `session_memory` (`memory/session_manager.py`), `product_repository`, `price_watcher_service`, `rag_service`, `category_resolver`... Riêng `session_memory` được import trực tiếp ở `core/graph.py`, `core/flows/clarification.py`, `core/flows/suggestions.py`, `core/agents/advisor_context.py`, `application/chat.py`.
- **Vấn đề**: các hàm trong `core/` đọc và ghi bộ nhớ hội thoại qua biến toàn cục.
- **Vì sao khó bảo trì**: nhìn chữ ký hàm không biết nó phụ thuộc vào gì. Test phải `monkeypatch` vào `session_factory` (xem `tests/integration/test_auth.py`). Muốn chạy nhiều worker thì bộ nhớ RAM không chia sẻ được giữa các worker.
- **Đề xuất**: chưa cần dùng framework DI. Trước mắt truyền `session_memory` qua constructor của `ShopAIAgentWorkflow` (đã có `get_workflow()` dùng `lru_cache` trong `src/dependencies/providers.py`), rồi các flow nhận nó qua tham số.
- **Ưu tiên**: Low (để giai đoạn 3). **Rủi ro**: Trung bình, chạm nhiều chữ ký hàm.

### B. Kiểu dữ liệu

#### B1. Sản phẩm là `dict[str, Any]` ở mọi tầng
- **Vị trí**: 3046 chỗ dùng `dict[str, Any]` trong backend. `shared/types.py` có `RawProduct` (TypedDict, `total=False`) nhưng chỉ được dùng 29 chỗ. Trong `product_repo.py`, `_field(item, camel, snake, default)` phải đọc cả `currentPrice` lẫn `current_price`.
- **Vấn đề**: cùng một sản phẩm có ít nhất 3 hình dạng: dict thô của sàn, dict đã xử lý (`data_processor.process_product`), và `ProductItemModel` (pydantic). Khóa lúc camel lúc snake.
- **Vì sao khó bảo trì**: gõ sai `"currentPrce"` không có lỗi kiểu nào báo, chỉ âm thầm ra `None`. Người mới không biết một dict có những khóa nào nếu không lần theo luồng chạy.
- **Đề xuất**: làm dần từng bước, không đổi hết một lần:
  1. Bổ sung đủ khóa vào `RawProduct` và dùng nó cho kiểu trả về của `data_processor.process_product` và `EcomSearchTool.run`.
  2. Chỉ dùng khóa camelCase (khớp API) cho dict sản phẩm, bỏ nhánh snake trong `_field`.
- **Ưu tiên**: **Critical**, vì đây là nguồn rủi ro lớn nhất khi sửa bất kỳ tính năng nào liên quan đến sản phẩm. **Rủi ro**: Thấp nếu chỉ thêm chú thích kiểu (không đổi lúc chạy); trung bình nếu bỏ khóa snake.

#### B2. Giá trị mặc định "bịa" khi thiếu dữ liệu
- **Vị trí**:
  - `integrations/platforms/link_reader.py`, `read_generic`: `rating=5.0`, `aiMatchScore=90`, `brand="Chính hãng"`, `warranty="Theo chính sách gian hàng"`;
  - `services/catalog/data_processor.py`, `process_product`: `aiMatchScore` mặc định 90, `warranty` mặc định "Chính hãng";
  - `frontend/src/services/agentApi.ts`, `toProductItem`: `inStock: true` cứng.
- **Vấn đề**: thiếu dữ liệu nhưng lại hiển thị như thật, ví dụ 5 sao cho một trang lạ.
- **Vì sao khó bảo trì**: không phân biệt được "không có dữ liệu" với "dữ liệu tốt". Ranker và advisor coi những số này là thật.
- **Đề xuất**: dùng `None` hoặc `0` cùng nhãn "Chưa có đánh giá" (frontend đã có sẵn nhánh `rating > 0`). Xem lại từng nơi đọc `aiMatchScore` trước khi đổi.
- **Ưu tiên**: High. **Rủi ro**: Trung bình, làm thay đổi thứ tự xếp hạng và nội dung hiển thị, nên cần xem với người làm sản phẩm.

### C. Độ phức tạp của hàm

#### C1. `core/tools/spec_comparator.py`, `build_table` (32 nhánh, 52 dòng)
- **Vấn đề**: một hàm vừa dựng cột, vừa định nghĩa hàm con `add_row`, vừa quyết định hàng nào "cao là tốt" bằng danh sách cứng `("RAM", "Lưu trữ", "Pin", ...)` viết lẫn trong biểu thức điều kiện, vừa định dạng chuỗi tiếng Việt.
- **Vì sao khó bảo trì**: thêm một thông số mới cần so sánh "thấp là tốt" phải sửa ngay giữa biểu thức ba ngôi.
- **Đề xuất**: đưa luật "tốt nhất" thành bảng hằng `SPEC_BEST = {"RAM": "max", ..., "Khối lượng": "min"}` cạnh `PREFERRED_SPEC_ROWS` trong `shared/spec_rows.py`, và tách `add_row` ra thành hàm `_best_index(values, rule)` ở cấp module.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp; đã có test so sánh trong `tests/unit/test_compare_categories.py`.

#### C2. Parser của từng sàn: `fpt.py parse_fpt_search` (28 nhánh), `tiki.py _search_once` (22), `cellphones.py parse_cellphones_search` (21)
- **Vấn đề**: mỗi parser vừa giải mã khung dữ liệu riêng của sàn (RSC push của FPT, API Tiki), vừa ánh xạ từng trường, vừa lọc bản ghi lỗi. Ví dụ `parse_fpt_search` có 4 chỗ `return []` sớm, sau đó là vòng lặp ánh xạ 12 trường.
- **Vì sao khó bảo trì**: sàn đổi cấu trúc thì khó biết hỏng ở bước giải mã hay bước ánh xạ.
- **Đề xuất**: tách mỗi parser thành 2 hàm: `_extract_items(html) -> list[dict]` (giải mã khung) và `_to_product(item) -> RawProduct | None` (ánh xạ một bản ghi). Không cần lớp hay pattern mới.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp; có fixture HTML trong `tests/fixtures/` và test `test_fpt_cellphones.py`, `test_mwg_price_and_model.py`.

#### C3. `integrations/llm/client.py`, `get_chat_model` (18 nhánh, 53 dòng)
- **Vấn đề**: dựng bảng nhà cung cấp, sắp thứ tự ưu tiên, kiểm tra kết nối mạng (`is_reachable`), tạo client, chọn `max_retries`, rồi ghép fallback, tất cả trong một hàm. Ngoài ra hàm này được gọi lại ở mỗi agent, và mỗi lần đều kiểm tra kết nối.
- **Vì sao khó bảo trì**: thêm nhà cung cấp mới phải sửa ở 3 chỗ trong cùng một hàm: bảng `candidates`, danh sách thứ tự `("deepseek", "openrouter", "groq")`, và `shared/config.py`.
- **Đề xuất**: chuyển bảng nhà cung cấp thành hằng `PROVIDERS` ở cấp module (tên → hàm đọc key, url, model từ settings), rồi tách `_ordered_providers()` và `_build_client(...)`.
- **Ưu tiên**: Low. **Rủi ro**: Thấp; có `tests/unit/test_llm_providers.py`.

#### C4. `services/catalog/ranker.py`, `_score_preference` và các hàm chấm điểm
- **Vấn đề**: `criteria: Any` đi kèm `getattr(criteria, "brands", None)` lặp lại 4 lần, vì hàm không biết chắc kiểu của tiêu chí.
- **Đề xuất**: khai báo đúng kiểu tiêu chí (liên quan A1); bỏ `getattr` phòng thủ khi kiểu đã chắc chắn.
- **Ưu tiên**: Low. **Rủi ro**: Thấp.

### D. Trùng lặp

#### D1. Frontend đoán lại "hãng" dù backend đã gửi
- **Vị trí**:
  - `frontend/src/services/agentApi.ts`: `KNOWN_BRANDS`, `GENERIC_WORDS`, `inferBrand` (khoảng 15 dòng regex);
  - backend: `services/catalog/data_processor.py`, `extract_brand`, có ghi `"brand"` vào sản phẩm.
- **Vấn đề**: type `BackendProduct` (`frontend/src/types.ts`) không khai báo trường `brand`, nên frontend bỏ qua dữ liệu backend gửi và tự đoán lại bằng danh sách hãng riêng.
- **Vì sao khó bảo trì**: hai danh sách hãng ở hai nơi sẽ lệch nhau; thêm hãng mới phải sửa cả hai.
- **Đề xuất**: thêm `brand?: string` vào `BackendProduct`, dùng `p.brand || inferBrand(p.name)` (giữ `inferBrand` làm dự phòng cho dữ liệu cũ đã lưu), rồi bỏ dần.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp, nhưng hãng hiển thị có thể khác trước ở vài sản phẩm.

#### D2. Ưu/nhược điểm tách bằng regex trên câu tiếng Việt của backend
- **Vị trí**:
  - frontend: `agentApi.ts` `NEGATIVE_REASON = /^(không|vượt|chưa|thiếu|ít)/i`, dùng để chia `matchReasons` thành `pros`/`cons`;
  - backend: `services/catalog/ranker.py` sinh các câu "Đúng yêu cầu…", "Không đúng yêu cầu…", "Vượt ngân sách…".
- **Vấn đề**: hai bên ràng buộc ngầm qua chữ cái đầu của câu tiếng Việt.
- **Vì sao khó bảo trì**: chỉ cần sửa câu "Vượt ngân sách" thành "Cao hơn ngân sách" là một nhược điểm hiện thành ưu điểm, mà không test nào báo.
- **Đề xuất**: backend trả lý do có cấu trúc, ví dụ `{"text": ..., "positive": bool}` hoặc hai danh sách `matchReasons` / `mismatchReasons`. Giữ trường cũ một thời gian để tương thích.
- **Ưu tiên**: High. **Rủi ro**: Thấp nếu thêm trường mới song song với trường cũ.

#### D3. Định dạng ngày giờ lặp lại ở frontend
- **Vị trí**: `App.tsx:32` (`formatNow`), `DataWarehousePanel.tsx:9`, `FeedbackInboxView.tsx:21`, `PriceAlertsView.tsx:19`, `PriceHistoryChart.tsx:18-19`, `SearchAssistantView.tsx` (`nowTime`). Đều là `toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', [year] })`.
- **Đề xuất**: thêm `formatDateTime(date, { withYear })` vào `i18n/index.tsx`, cạnh `formatVnd` vừa được gom lại trong đợt refactor trước.
- **Ưu tiên**: Low. **Rủi ro**: Rất thấp.

#### D4. Chuỗi User-Agent lặp lại với nhiều phiên bản khác nhau
- **Vị trí**: `integrations/platforms/common.py` (`BROWSER_UA`, Chrome 124), `integrations/platforms/link_reader.py` (Chrome 120), `integrations/policy_pages.py` (Chrome 124 viết rút gọn), `scripts/rag/reindex.py` (Chrome 120).
- **Đề xuất**: dùng chung `BROWSER_UA`. Lưu ý: header gửi lên sàn sẽ thay đổi, nên chạy `make test-live` để kiểm tra sàn không chặn.
- **Ưu tiên**: Low. **Rủi ro**: Thấp đến trung bình (phản ứng chống bot của sàn).

### E. Đa ngôn ngữ (i18n)

#### E1. Backend trả câu tiếng Việt cứng, frontend dịch lại bằng bảng tra và regex
- **Vị trí**:
  - backend: `core/tools/spec_comparator.py` ("Giá hiện tại", "Giảm giá", "Bảo hành"...), `core/flows/search_flow.py` (thông báo status), `services/catalog/ranker.py` (lý do), `shared/exceptions` (thông báo lỗi). Riêng `core/i18n.py` cùng `core/locales/` chỉ được dùng cho `clarify.*` và `suggest.*`;
  - frontend: `src/i18n/en.ts` có 462 khóa là câu tiếng Việt gốc, cộng `EN_PATTERNS` (8 regex) cho câu có biến.
- **Vấn đề**: sửa một chữ trong câu backend là mất bản dịch tiếng Anh mà không có cảnh báo. `npm run i18n:check` chỉ kiểm được chuỗi nằm trong frontend.
- **Vì sao khó bảo trì**: mỗi lần đổi nội dung câu phải sửa cả hai repo, và phải đoán đúng regex.
- **Đề xuất**: với câu có cấu trúc (nhãn hàng so sánh, status, lỗi), backend trả **mã kèm tham số** (`{"code": "rate_limited", "params": {"seconds": 42}}`) cùng `detail` tiếng Việt để tương thích; frontend dịch theo mã. Làm dần cho các câu hay đổi trước. Ngoài ra, backend đã nhận `language` trong `ChatRequest`, nên có thể dùng `core/i18n.tr()` cho phần chat.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp nếu làm song song (giữ `detail` cũ).

### F. Tài liệu

#### F1. `docs/` lệch với cấu trúc code hiện tại
- **Vị trí**: `docs/07-folder-structure.md`, `docs/api/README.md`, `docs/architecture/arc42/05-building-block-view.md`, `docs/architecture/arc42/11-risks-and-technical-debt.md`, `docs/architecture/c4/01-system-context.md`, `docs/reviews/F01-*.md`, `F02-*.md` vẫn nhắc `src/config.py`, `src/auth.py`, `services/catalog/platforms`, `_legacy` (đã chuyển chỗ hoặc đã xóa).
- **Vì sao khó bảo trì**: người mới đọc tài liệu sẽ tìm sai chỗ. `backend/README.md` mới là nguồn đúng.
- **Đề xuất**: cập nhật hoặc đánh dấu "lỗi thời" ở các file trên; trỏ về `backend/README.md` làm nguồn chính cho cấu trúc thư mục.
- **Ưu tiên**: High (rẻ mà lợi lớn). **Rủi ro**: Không có.

### G. Frontend: state và trách nhiệm

#### G1. `SearchAssistantView.tsx`: một component làm 4 việc
- **Vị trí**: `frontend/src/components/SearchAssistantView.tsx` (676 dòng): 12 state/hook; `handleSendQuery` (khoảng 65 dòng) dựng một `draft` có thể thay đổi qua 7 callback SSE; `handleCompareProducts`; quản lý danh sách hội thoại; render toàn bộ tin nhắn, thẻ hỏi làm rõ và ô nhập.
- **Vấn đề**: logic luồng chat (gửi, nhận stream, ghép tin nhắn, xử lý lỗi) nằm lẫn trong JSX.
- **Vì sao khó bảo trì**: không test được luồng chat nếu không render cả màn hình. Sửa giao diện tin nhắn dễ đụng vào logic stream.
- **Đề xuất**: tách custom hook `useChatSession(userId)` trả về `{ conversations, activeConversation, messages, send, compare, busy, reasoning }`, chứa `handleSendQuery`, `handleCompareProducts` và CRUD hội thoại. Phần render tin nhắn tách thành `chat/MessageBubble.tsx`; thẻ hỏi làm rõ thành `chat/ClarificationCard.tsx`. Đợt trước đã tách `chat/ProductCard.tsx` và `chat/CitationPanel.tsx`.
- **Ưu tiên**: High. **Rủi ro**: Trung bình, vì luồng SSE có trạng thái trung gian (`draft`, `upsert`); cần kiểm tra tay hoặc viết test cho hook.

#### G2. `App.tsx`: điều phối mọi tính năng
- **Vị trí**: `frontend/src/App.tsx` (363 dòng), khoảng 16 state: tab, 4 modal, nguồn dữ liệu bật/tắt, chính sách, yêu cầu chat, lịch sử, sản phẩm đã lưu, hoạt động, sản phẩm đang theo dõi, số góp ý mới. Các handler `handleToggleSave`, `handleResults`, `askAgentToCompare`, `handleChangePlatforms` vừa đổi state vừa ghi nhật ký hoạt động (`logActivity`).
- **Vấn đề**: thêm một tính năng là phải sửa `App.tsx`; props truyền xuống `SearchAssistantView` có 9 prop.
- **Đề xuất**: gom theo tính năng thành hook: `useSavedProducts(userId, logActivity)`, `useActivityLog(userId)`, `useSearchHistory(userId)`. `App.tsx` chỉ còn điều hướng tab và modal. Chưa cần Redux hay Context toàn cục; chỉ dùng Context cho `logActivity` nếu prop truyền quá sâu.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp đến trung bình.

#### G3. Cache chính sách bằng biến toàn cục ngoài React
- **Vị trí**: `frontend/src/services/shoppingService.ts`: `let policyCache`, `setPolicyCache`, `getPolicy`.
- **Vấn đề**: component đọc `getPolicy()` lúc render sẽ không tự render lại khi cache đổi. Hiện vẫn chạy đúng nhờ `App` giữ state `policies` song song.
- **Đề xuất**: truyền `policies` qua props hoặc một Context nhỏ, rồi bỏ biến toàn cục.
- **Ưu tiên**: Low. **Rủi ro**: Thấp.

### H. Frontend: tầng gọi API

#### H1. `services/agentApi.ts` trộn 4 trách nhiệm
- **Vị trí**: `frontend/src/services/agentApi.ts` (413 dòng):
  - (1) HTTP client và token (`apiFetch`, `getToken`, `errorDetail`);
  - (2) chuyển đổi dữ liệu (`toProductItem`, `fromProductItem`, `toComparison`, `inferBrand`, `parseVolume`);
  - (3) SSE (`streamChat`, `dispatch`);
  - (4) khoảng 25 hàm endpoint (auth, alerts, crawler, user data...).
- **Vấn đề khác**: `PLATFORM_IDS` là bảng ánh xạ "định danh" (`tgdd → 'tgdd'`...), cộng thêm `BACKEND_PLATFORMS` đảo ngược lại, tức là một lớp trừu tượng không làm gì.
- **Đề xuất**: tách thành `services/http.ts` (client và token), `services/mappers.ts` (chuyển đổi, là hàm thuần nên dễ test), `services/chatStream.ts`, và endpoint theo tính năng (`services/alertsApi.ts`...). Bỏ `PLATFORM_IDS` sau khi xác nhận không còn tên sàn nào khác nhau giữa hai bên.
- **Ưu tiên**: Medium. **Rủi ro**: Thấp, chủ yếu chuyển chỗ và đổi đường dẫn import.

### I. Kiểm thử và công cụ

#### I1. Frontend không có test nào
- **Vị trí**: không có file `*.test.*` trong `frontend/src`; `package.json` không có script `test`.
- **Vì sao khó bảo trì**: mọi refactor ở mục G và H đều phải kiểm tra bằng tay.
- **Đề xuất**: khi đã được phép thêm dev-dependency, thêm Vitest (cùng hệ sinh thái Vite) và viết test cho các hàm thuần trước: `mappers` (`toProductItem`, `toComparison`), `translate` cùng `EN_PATTERNS`, `formatVnd`. Chưa cần test component.
- **Ưu tiên**: High. **Rủi ro**: Không có (chỉ thêm).

#### I2. Ruff chưa được khai báo trong dependency
- **Vị trí**: `backend/pyproject.toml` và `Makefile` (`make lint`) dùng ruff, nhưng `requirements.txt` không có ruff.
- **Đề xuất**: thêm `requirements-dev.txt` (gồm ruff, pytest...) để máy khác chạy được `make lint`.
- **Ưu tiên**: Low. **Rủi ro**: Không có.

#### I3. Frontend không có linter hay formatter
- **Vị trí**: `frontend/package.json` (`"lint": "tsc --noEmit"`).
- **Đề xuất**: cân nhắc ESLint (`react-hooks/exhaustive-deps` bắt được lỗi `useEffect` thiếu dependency) và Prettier. Đây là dependency mới nên cần cả team đồng ý.
- **Ưu tiên**: Low. **Rủi ro**: Không có (format lần đầu sẽ tạo diff lớn, nên tách thành commit riêng).

---

## 3. Top 10 cơ hội refactor

Xếp theo (giá trị cho việc bảo trì) ÷ (chi phí + rủi ro).

| # | Việc | Mục | Ưu tiên | Rủi ro |
|---|---|---|---|---|
| 1 | Kiểu dữ liệu sản phẩm thống nhất (`RawProduct` đầy đủ, chỉ dùng camelCase) | B1 | Critical | Thấp → TB |
| 2 | Cập nhật `docs/` theo cấu trúc hiện tại | F1 | High | Không |
| 3 | Backend trả lý do có cấu trúc thay cho regex tiếng Việt ở frontend | D2 | High | Thấp |
| 4 | Tách `useChatSession` ra khỏi `SearchAssistantView` | G1 | High | TB |
| 5 | Thêm test cho các hàm chuyển đổi ở frontend | I1 | High | Không |
| 6 | Bỏ giá trị mặc định "bịa" (rating 5.0, aiMatchScore 90, inStock true) | B2 | High | TB |
| 7 | Sửa import ngược ở `integrations` (`sold_label` → `shared`, `SearchQuery` nhỏ) | A1 | High | Thấp |
| 8 | Tách `agentApi.ts` thành http, mappers, stream, endpoint theo tính năng | H1 | Medium | Thấp |
| 9 | Tách service đọc giá khỏi job nền (`application/alerts` không gọi `jobs/`) | A3 | Medium | TB |
| 10 | Bảng luật cho `spec_comparator.build_table`; tách parser của sàn thành giải mã + ánh xạ | C1, C2 | Medium | Thấp |

---

## 4. Lộ trình

### Giai đoạn 1: việc nhanh (mỗi việc vài giờ, ít rủi ro)
| Việc | File | Kiểm tra |
|---|---|---|
| Cập nhật hoặc đánh dấu lỗi thời ở `docs/` (F1) | `docs/07-folder-structure.md`, `docs/api/README.md`, `docs/architecture/**` | Đọc lại; `grep -r "src/config.py" docs` không còn kết quả |
| Hàm `formatDateTime` dùng chung (D3) | `frontend/src/i18n/index.tsx` và 5 file dùng | `npm run lint`, `npm run build`, xem tay các màn có ngày giờ |
| Dùng `brand` của backend, `inferBrand` chỉ làm dự phòng (D1) | `frontend/src/types.ts`, `services/agentApi.ts` | `npm run lint`; so sánh hãng hiển thị trên vài sản phẩm |
| Bảng `SPEC_BEST` cho `build_table` (C1) | `core/tools/spec_comparator.py`, `shared/spec_rows.py` | `pytest tests/unit/test_compare_categories.py` |
| Chuyển `sold_label` vào `shared/` (một phần A1) | `services/catalog/reviews.py`, `integrations/platforms/{fpt,mwg}.py` | `ruff check`, `pytest tests/unit` |
| Thêm `requirements-dev.txt` (I2) | `backend/` | `pip install -r requirements-dev.txt && make lint` |

### Giai đoạn 2: tái cấu trúc (mỗi việc 1–3 ngày, làm theo từng PR riêng)
| Việc | File | Rủi ro và cách giảm |
|---|---|---|
| `RawProduct` đầy đủ, chú thích kiểu cho các hàm xử lý sản phẩm (B1, bước 1) | `shared/types.py`, `services/catalog/data_processor.py`, `core/tools/ecom_search.py`, `core/tools/search_sources.py` | Chỉ thêm kiểu, chưa đổi lúc chạy; chạy toàn bộ test |
| Lý do có cấu trúc (D2) | `services/catalog/ranker.py`, `src/schemas/product.py`, `frontend/src/services/agentApi.ts` | Giữ `matchReasons` cũ song song |
| Thêm Vitest và test cho mappers (I1) | `frontend/` | Cần đồng ý thêm dev-dependency |
| `useChatSession` và tách `MessageBubble`, `ClarificationCard` (G1) | `frontend/src/components/SearchAssistantView.tsx`, `hooks/` | Làm sau khi đã có test mappers; kiểm tra tay luồng chat, so sánh, hỏi làm rõ, lỗi mạng |
| Hook theo tính năng cho `App.tsx` (G2) | `frontend/src/App.tsx`, `hooks/` | Kiểm tra tay lưu/bỏ lưu, nhật ký hoạt động, theo dõi giá |
| Tách `agentApi.ts` (H1) | `frontend/src/services/` | Chỉ chuyển chỗ; `tsc` bắt lỗi import |
| Sửa import ngược còn lại (A1 `SearchQuery`, A2 `categorize` ra khỏi repository) | `integrations/platforms/*`, `database/repositories/product_repo.py`, các nơi gọi `upsert_products` | Test tích hợp `test_product_repository.py`, `test_price_alerts.py` |
| Service đọc giá dùng chung (A3) | `jobs/price_watcher.py`, `application/alerts.py`, `services/pricing/` | Giữ nguyên `_confirm_drop`, nhật ký; test hiện có |
| Bỏ giá trị mặc định bịa (B2) | `link_reader.py`, `data_processor.py`, `agentApi.ts` | Thay đổi hành vi có chủ đích; cần người làm sản phẩm duyệt |
| Mã lỗi/mã thông báo cho i18n (E1), làm dần | `shared/exceptions.py`, `src/errors.py`, `frontend/src/i18n/` | Giữ `detail` cũ |

### Giai đoạn 3: kiến trúc (chỉ làm khi có nhu cầu thật)
| Việc | Khi nào cần |
|---|---|
| Truyền `session_memory` và repository qua constructor thay vì singleton (A4) | Khi test bị vướng monkeypatch nhiều, hoặc cần chạy nhiều cấu hình song song |
| Lưu bộ nhớ hội thoại, bộ đếm rate limit và khóa đăng nhập ngoài process (Redis) | Khi chạy nhiều worker hoặc nhiều máy; hiện tại đều nằm trong RAM của một process (`memory/session_manager.py`, `src/dependencies/rate_limit.py`, `services/auth/service.py LoginThrottle`) |
| Hợp nhất hẳn `ProductItemModel` và `RawProduct` (B1, bước cuối) | Sau khi giai đoạn 2 cho thấy hai kiểu trùng nhau gần hết |

---

## 5. Những việc không nên làm

- **Không tách file chỉ để file ngắn hơn.** `mwg.py`, `product_repo.py` dài nhưng mỗi hàm làm một việc rõ ràng; `data_processor.process_product` dài 55 dòng nhưng chỉ ánh xạ từng trường một, đọc vẫn dễ.
- **Không viết lại `core/graph.py`.** StateGraph hiện tại rõ ràng và đã có test.
- **Không thêm framework DI, Redux hay pattern Repository/UnitOfWork mới.** Vấn đề hiện tại giải quyết được bằng truyền tham số và custom hook.
- **Không đổi tên trường API** (camelCase) vì frontend và dữ liệu đã lưu của người dùng (`user_data`) phụ thuộc vào nó.
- **Không gộp mọi `except Exception` còn lại.** Cả 6 chỗ đều là chốt chặn có chủ đích, đã có chú thích (vòng lặp nền, SSE, warmup, seed script).
