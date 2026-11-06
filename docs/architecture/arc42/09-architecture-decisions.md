# 9. Quyết định kiến trúc

Mỗi ADR gồm: Bối cảnh, Quyết định, Phương án khác, Hệ quả, Trạng thái. **Đã áp dụng** = có trong mã nguồn hiện tại.

## ADR-001 LangGraph StateGraph điều phối agent

| | |
|---|---|
| **Bối cảnh** | Luồng xử lý có nhiều nhánh (làm rõ, link, tìm kiếm, săn deal, tư vấn chung). Phiên bản đầu là chuỗi if/else viết hai lần cho API thường và API stream, hai bản đã lệch nhau. |
| **Quyết định** | Một `StateGraph` trên `AgentState`; node phát sự kiện qua `get_stream_writer()`. `ainvoke` cho `/chat`, `astream(stream_mode="custom")` cho `/chat/stream`. |
| **Phương án khác** | Giữ if/else; agent tự do kiểu ReAct (khó kiểm soát số lần gọi LLM và tính trung thực). |
| **Hệ quả** | Một nguồn logic duy nhất; dễ thêm node; test đồ thị bằng stub. |
| **Trạng thái** | Đã áp dụng |

## ADR-002 LLM chỉ hiểu và diễn đạt, không quyết định dữ liệu

| | |
|---|---|
| **Bối cảnh** | LLM có thể "bịa" giá, cấu hình. |
| **Quyết định** | LLM dùng cho: phân loại ý định / trích tiêu chí, lọc ngữ nghĩa, soạn lời tư vấn từ ngữ cảnh chuẩn hóa. Xếp hạng, đối chiếu thông số, so sánh, nới lỏng là mã xác định. |
| **Hệ quả** | Kết quả lặp lại được, kiểm thử được; prompt advisor có quy tắc dữ liệu (BR-005). |
| **Trạng thái** | Đã áp dụng |

## ADR-003 Chuỗi dự phòng nhiều nhà cung cấp LLM

| | |
|---|---|
| **Quyết định** | `get_chat_model` dựng `ChatOpenAI` cho DeepSeek, OpenRouter, Groq theo thứ tự ưu tiên `LLM_PROVIDER`, nối bằng `with_fallbacks`; timeout 45 s, 1 lần thử lại. |
| **Phương án khác** | Một nhà cung cấp; tự viết vòng thử lại trong từng agent (đã bỏ vì trùng lặp). |
| **Hệ quả** | Một nhà cung cấp lỗi không làm hỏng lượt tư vấn. |
| **Trạng thái** | Đã áp dụng |

## ADR-004 Thu thập dữ liệu bằng HTTP + BeautifulSoup, cache-first

| | |
|---|---|
| **Bối cảnh** | Không có API chính thức của TGDĐ/ĐMX; trang danh mục render sẵn phía máy chủ; tìm kiếm từ khóa dài render bằng JavaScript. |
| **Quyết định** | `httpx` + BeautifulSoup, bộ phân tích dựa trên cấu trúc (ảnh + giá) thay vì tên class; Tiki dùng API JSON. Tra cache SQLite → ChromaDB trước khi cào. |
| **Phương án khác** | Playwright cho mọi trang (chậm, nặng); chỉ dùng API Tiki (thiếu nguồn). |
| **Hệ quả** | Nhanh, nhẹ; chỉ lấy được ~20 sản phẩm đầu của trang danh mục TGDĐ (nợ kỹ thuật TD-01). |
| **Trạng thái** | Đã áp dụng |

## ADR-005 Làm giàu từ trang chi tiết

| | |
|---|---|
| **Quyết định** | Đọc trang chi tiết để lấy thông số chuẩn hóa nhãn, bảo hành, đổi trả; giá hiện tại đọc từ JSON-LD. Cache 6 giờ, tối đa 6 yêu cầu đồng thời. |
| **Hệ quả** | Phát hiện được sai cấu hình (VD máy ghi "gaming" nhưng GPU RTX 3050); tốn thêm vài giây mỗi lượt. |
| **Trạng thái** | Đã áp dụng |

## ADR-006 SQLite + ChromaDB nhúng

| | |
|---|---|
| **Quyết định** | SQLite (SQLAlchemy async) cho dữ liệu quan hệ; ChromaDB nhúng cho RAG. |
| **Phương án khác** | PostgreSQL + pgvector (cần cài máy chủ CSDL). |
| **Hệ quả** | Chạy ngay trên máy cá nhân; giới hạn một worker ghi; khóa CSDL khi nhiều tiến trình cùng ghi. |
| **Trạng thái** | Đã áp dụng |

## ADR-007 Server-Sent Events cho tư vấn

| | |
|---|---|
| **Quyết định** | `POST /api/chat/stream` trả SSE với các sự kiện có kiểu (`status`, `products`, `comparison`, `clarification`, `token`, `suggestions`, `done`, `error`). Frontend đọc bằng `fetch` + `ReadableStream` (gửi được header). |
| **Phương án khác** | WebSocket (hai chiều, phức tạp hơn mức cần); trả một lần (người dùng chờ 20–30 s không thấy gì). |
| **Trạng thái** | Đã áp dụng |

## ADR-008 Token phiên lưu băm thay vì JWT

| | |
|---|---|
| **Bối cảnh** | Cần đăng xuất / đổi mật khẩu có hiệu lực ngay. |
| **Quyết định** | Token ngẫu nhiên 256 bit; DB lưu SHA-256 và hạn 30 ngày; kiểm tra mỗi yêu cầu. Mật khẩu bcrypt. |
| **Phương án khác** | JWT không trạng thái (không thu hồi được trước hạn nếu không có danh sách đen). |
| **Hệ quả** | Thu hồi tức thì; thêm một truy vấn CSDL mỗi yêu cầu. |
| **Trạng thái** | Đã áp dụng |

## ADR-009 Nâng cấp lược đồ bằng `_add_missing_columns`

| | |
|---|---|
| **Quyết định** | Khi khởi động: `create_all` rồi thêm cột thiếu bằng `ALTER TABLE ADD COLUMN`. |
| **Phương án khác** | Alembic (thêm bước di chuyển, phức tạp với nhóm nhỏ). |
| **Hệ quả** | Nâng cấp không mất dữ liệu cho thay đổi cộng thêm; đổi kiểu / xóa cột phải làm tay. |
| **Trạng thái** | Đã áp dụng |

## ADR-010 Trạng thái hội thoại lưu bền

| | |
|---|---|
| **Quyết định** | Câu hỏi làm rõ đang chờ và ngành hàng đã hỏi lưu trong `conversation_states`; ghi tuần tự theo phiên. |
| **Hệ quả** | Không mất khi khởi động lại; vẫn có bộ nhớ đệm trong RAM nên chưa an toàn cho nhiều worker. |
| **Trạng thái** | Đã áp dụng |

## ADR-011 Dữ liệu giao diện theo tài khoản dạng khóa – giá trị

| | |
|---|---|
| **Quyết định** | Hội thoại, đã lưu, lịch sử, tìm kiếm gần đây lưu nguyên khối JSON trong `user_data(user_id, key)`; frontend `useSyncedState` hiện bản trên máy rồi đồng bộ (gộp thay đổi 0,8 s). |
| **Phương án khác** | Bảng chuẩn hóa cho từng loại (nhiều API CRUD). |
| **Hệ quả** | Ít API, nhanh làm; ghi đè cả khối, giới hạn 2 MB / khóa; hai thiết bị sửa cùng lúc thì bản sau thắng. |
| **Trạng thái** | Đã áp dụng |

## ADR-012 Chế độ tối bằng định nghĩa lại biến màu

| | |
|---|---|
| **Quyết định** | Định nghĩa lại `--color-*` của Tailwind dưới `.dark` thay vì thêm `dark:` vào từng class. |
| **Hệ quả** | Mọi màn hình đổi theo một chỗ; màu nhấn được chọn lại cho đủ tương phản. |
| **Trạng thái** | Đã áp dụng |

## ADR-013 Embedding bge-m3 qua API và truy xuất lai BM25 + RRF

| | |
|---|---|
| **Bối cảnh** | ChromaDB mặc định dùng all-MiniLM-L6-v2 (tiếng Anh): "tai nghe chống ồn" ra chảo chống dính; recall@5 trên bộ đánh giá chỉ 0,28. Danh mục trong kho lẫn lộn; giá nằm trong văn bản nhúng. |
| **Quyết định** | Embedding `baai/bge-m3` qua OpenRouter (đã có key, chi phí không đáng kể) thay vì chạy mô hình cục bộ (~2,3 GB). Văn bản nhúng chỉ chứa thông tin ổn định; giá, đánh giá, thời điểm ở metadata. Thêm BM25 và hợp nhất RRF; chuẩn hóa danh mục khi nạp theo mã của sàn (luật tên dự phòng); ngưỡng hiệu chỉnh bằng bộ đánh giá 51 truy vấn. Collection mới `products_v2`. |
| **Hệ quả** | recall@5 0,28 → 0,88, MRR 0,46 → 0,88. Phụ thuộc thêm một API ngoài và thêm 1,5–5 s mỗi truy vấn mới; khi lỗi thì chỉ tìm từ khóa, không có gì đạt thì cào trực tiếp. Đổi mô hình phải reindex. |
| **Trạng thái** | Đã áp dụng ([11-rag.md](../../11-rag.md)) |

## Quyết định để sau

- Playwright cho trang render bằng JavaScript.
- PostgreSQL + Alembic + nhiều worker.
- Thông báo email / đẩy; quên mật khẩu.
- RAG cho chính sách bảo hành / đổi trả; reranker cho RAG sản phẩm.
