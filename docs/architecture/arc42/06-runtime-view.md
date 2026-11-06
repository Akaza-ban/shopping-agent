# 6. Góc nhìn thời gian chạy

## 6.1 Đăng nhập

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant W as Web App
    participant A as Auth API
    participant R as UserRepository
    U->>W: Email + mật khẩu
    W->>A: POST /api/auth/login
    A->>A: Kiểm tra khóa tạm (LoginThrottle)
    A->>R: get_by_email
    A->>A: bcrypt.checkpw (hash giả nếu không có email)
    alt Sai
        A-->>W: 401 "Email hoặc mật khẩu không đúng"
    else Đúng
        A->>R: create_token(SHA-256(token), 30 ngày)
        A-->>W: {token, user}
        W->>A: GET /api/auth/me/data/{key} (đồng bộ dữ liệu cá nhân)
    end
```

## 6.2 Tư vấn mua sắm (đồ thị LangGraph)

```mermaid
stateDiagram-v2
    [*] --> load_session
    load_session --> route
    route --> clarify
    clarify --> ask: cần làm rõ
    clarify --> parse_link: parse_link
    clarify --> search: search / compare
    clarify --> deal: find_deal
    clarify --> respond: general_advice / out_of_scope
    ask --> finalize
    parse_link --> respond
    search --> compare
    deal --> compare
    compare --> respond
    respond --> finalize
    finalize --> [*]
```

Trình tự một lượt tìm mua: xem [UML trình tự §2](../uml/02-sequence-diagrams.md#2-tư-vấn-mua-sắm--post-apichatstream). Điểm chính:

1. `_own_session` gắn / kiểm tra chủ hội thoại (`403` nếu của người khác).
2. Node `route`: gọi LLM một lần lấy JSON `{intent, criteria}`; áp `platform` từ giao diện.
3. Node `search` (`_run_search`): `EcomSearchTool.run` → nếu rỗng thì nới lỏng; nếu không sản phẩm nào đúng thông số thì tìm thêm +20% ngân sách.
4. Mỗi node phát sự kiện qua `get_stream_writer()`; route SSE chuyển thẳng sang trình duyệt.

## 6.3 Tìm kiếm cache-first

```mermaid
flowchart TB
    q["EcomSearchTool.run"] --> c{"search_cache còn hạn?"}
    c -- có --> fin["_finalize: làm giàu → đối chiếu → xếp hạng → ghi độ mới"]
    c -- không --> r{"ChromaDB có kết quả qua lọc ngữ nghĩa?"}
    r -- có --> fin
    r -- không --> crawl["Cào song song TGDĐ, ĐMX, Tiki"]
    crawl --> clean["Làm sạch + lọc ngữ nghĩa"]
    clean --> fin
    fin --> save["Lưu products, price_history, search_cache, ChromaDB"]
```

## 6.4 Theo dõi giá

```mermaid
sequenceDiagram
    participant T as Bộ lập lịch / API check
    participant W as PriceWatcherService
    participant E as ProductEnricher
    participant G as Guardrails
    participant DB as SQLite
    T->>W: check_alerts(ids?, user_id?)
    W->>DB: alerts status=watching
    loop mỗi yêu cầu
        W->>E: fetch_current_price (JSON-LD / API Tiki)
        alt Không đọc được
            W->>DB: last_note "Không đọc được giá"
        else Có giá
            W->>G: check_price, check_change
            alt Giá vô lý (laptop 100.000 đ)
                W->>DB: last_note "Bỏ qua giá đọc được"
            else Biến động bất thường, chưa khớp pending_price
                W->>DB: pending_price = giá mới, chờ lần sau
            else ≤ mục tiêu và giảm > 30%
                W->>E: đọc lại ngay
                W->>DB: khớp → triggered, lệch → pending_price
            else Hợp lệ
                W->>DB: upsert product (ghi mốc nếu đổi giá)
                W->>DB: last/lowest price, triggered nếu ≤ mục tiêu, xóa pending
            end
        end
    end
```

## 6.5 Lỗi thường gặp

| Tình huống | Hành vi |
|---|---|
| Token sai / hết hạn | `401`; giao diện phát sự kiện `shopping-ai:auth-expired` và về màn đăng nhập |
| LLM lỗi | Chuyển nhà cung cấp kế tiếp; tất cả lỗi → phân loại từ khóa / câu trả lời dựng sẵn |
| Sàn lỗi kết nối | Thử lại; nguồn khác vẫn trả kết quả; ghi chú cho người dùng |
| Lỗi trong stream | Sự kiện `error`; giao diện giữ phần đã nhận và hiện thông báo |
| Backend tắt | Giao diện hiện địa chỉ backend và lệnh khởi động |
