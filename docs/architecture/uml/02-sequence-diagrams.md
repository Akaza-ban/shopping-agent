# Biểu đồ trình tự

## 1. Đăng ký — `POST /api/auth/register`

```mermaid
sequenceDiagram
    actor G as Khách
    participant W as AuthView
    participant API as Auth API
    participant S as auth_service
    participant R as UserRepository
    G->>W: Tên, email, mật khẩu, nhập lại
    W->>W: Kiểm tra tại chỗ (email, ≥ 8 ký tự, chữ + số, khớp)
    W->>API: POST /api/auth/register
    API->>S: validate_registration
    alt Không hợp lệ
        API-->>W: 422 detail
    else Hợp lệ
        API->>S: hash_password (bcrypt)
        API->>R: create_user(role = admin nếu email ∈ ADMIN_EMAILS)
        alt Email đã có
            API-->>W: 409 "Email này đã được đăng ký."
        else
            API->>R: create_token(SHA-256(token), 30 ngày)
            API-->>W: 201 {token, user}
            W->>W: Lưu token, dựng ShoppingApp, chuyển dữ liệu cũ vào tài khoản
        end
    end
```

## 2. Tư vấn mua sắm — `POST /api/chat/stream`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as SearchAssistantView
    participant C as Chat API
    participant G as AgentWorkflow
    participant O as Orchestrator
    participant S as EcomSearchTool
    participant E as Enricher + Ranker
    participant A as Advisor
    participant L as LLM
    participant M as Sàn TMĐT
    participant DB as SQLite
    U->>V: Nhập yêu cầu
    V->>C: POST /chat/stream (Bearer, session_id, message, platform)
    C->>DB: claim_session (403 nếu của người khác)
    C->>G: execute_stream(state)
    G->>DB: load_session_from_db
    G-->>V: status routing
    G->>O: route(state)
    O->>L: ý định + tiêu chí
    L-->>O: JSON
    G->>G: clarify (gộp / hỏi làm rõ)
    G-->>V: status retrieval
    G->>S: run(query, criteria)
    S->>DB: search_cache / ChromaDB
    S->>M: cào song song (nếu cần)
    S->>L: lọc ngữ nghĩa
    S->>E: enrich + rank
    E->>M: trang chi tiết
    S-->>G: sản phẩm có điểm, lý do
    G-->>V: products
    G-->>V: comparison (≥ 2 sản phẩm)
    G->>A: generate_response_stream
    A->>L: ngữ cảnh chuẩn hóa
    loop token
        L-->>A: token
        G-->>V: token
    end
    G->>DB: save_turn
    G-->>V: suggestions, done(search_notes)
    V-->>U: Thẻ sản phẩm, bảng so sánh, lời tư vấn, lưu ý dữ liệu
```

## 3. Hỏi làm rõ qua hai lượt

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant G as AgentWorkflow
    participant M as SessionMemory
    participant DB as conversation_states
    U->>G: "Tư vấn giúp tôi tìm mua máy giặt"
    G->>G: _maybe_ask_clarification (không giá, hãng, model)
    G->>M: update_conversation_state(pending, clarified_categories)
    M->>DB: ghi tuần tự
    G-->>U: clarification {question, options}
    Note over G,DB: Máy chủ có thể khởi động lại ở đây
    U->>G: "5 - 10 triệu"
    G->>M: load_session_from_db (nạp state)
    G->>G: _apply_pending_clarification → gộp max_price, xóa pending
    G->>G: tiếp tục search → compare → respond
```

## 4. Kiểm tra giá — `POST /api/alerts/check`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as PriceAlertsView
    participant API as Alerts API
    participant W as PriceWatcher
    participant E as Enricher
    participant GR as Guardrails
    participant DB as SQLite
    U->>V: "Kiểm tra giá ngay"
    V->>API: POST /alerts/check {alert_ids}
    API->>W: check_alerts(ids, user_id)
    W->>DB: alerts watching của user
    loop mỗi yêu cầu
        W->>E: fetch_current_price
        E-->>W: giá (JSON-LD / API Tiki) hoặc None
        W->>GR: check_price, check_change
        alt Hợp lệ và ≤ mục tiêu
            opt giảm > 30%
                W->>E: đọc lại, phải khớp ±2%
            end
            W->>DB: ghi mốc giá, status = triggered
        else Hợp lệ
            W->>DB: last_price, lowest_price
        else Biến động bất thường
            W->>DB: pending_price, chờ lần đọc sau khớp
        else Giá vô lý / không đọc được
            W->>DB: last_note
        end
    end
    API-->>V: danh sách sau cập nhật
```

## 5. Xóa hội thoại — `DELETE /api/chat/history/{id}`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as ConversationList
    participant API as Chat API
    participant M as SessionMemory
    participant DB as SQLite
    U->>V: Thùng rác → "Xóa"
    V->>V: Xóa khỏi danh sách (đồng bộ user_data)
    V->>API: DELETE /chat/history/{id}
    API->>DB: get_session_owner
    alt Của người khác
        API-->>V: 403
    else
        API->>M: delete_session
        M->>DB: xóa chat_messages, conversation_states, chat_sessions
        API-->>V: {deleted: true}
    end
```

## 6. Đăng xuất — `POST /api/auth/logout`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant H as Header (menu tài khoản)
    participant AP as AuthProvider
    participant API as Auth API
    participant R as UserRepository
    U->>H: Mở menu → "Đăng xuất"
    H->>AP: logout()
    AP->>API: POST /auth/logout (Bearer)
    API->>R: delete_token(SHA-256(token))
    API-->>AP: 200 ok
    AP->>AP: Xóa token khỏi localStorage, user = null
    AP-->>U: Màn hình Đăng nhập
    Note over AP,API: Token hết hạn ở bất kỳ lời gọi nào → apiFetch nhận 401, phát sự kiện auth-expired, AuthProvider cũng về màn hình Đăng nhập
```

## 7. Đổi mật khẩu — `POST /api/auth/change-password`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant M as AccountModal
    participant API as Auth API
    participant S as auth_service
    participant R as UserRepository
    U->>M: Mật khẩu hiện tại, mật khẩu mới, nhập lại
    M->>M: Kiểm tra mật khẩu mới (≥ 8 ký tự, chữ + số) và khớp nhập lại
    M->>API: POST /auth/change-password
    API->>S: verify_password(hiện tại)
    alt Sai mật khẩu hiện tại
        API-->>M: 400 "Mật khẩu hiện tại không đúng."
    else Mật khẩu mới yếu
        API-->>M: 422
    else Hợp lệ
        API->>S: hash_password(mới)
        API->>R: update_user(password_hash)
        API->>R: delete_user_tokens(user_id, giữ token hiện tại)
        API-->>M: 200 ok
        M-->>U: "Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất."
    end
```

## 8. Nhờ AI so sánh sản phẩm đã lưu — `POST /api/chat/compare`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant SV as SavedProductsView
    participant APP as ShoppingApp
    participant V as SearchAssistantView
    participant API as Chat API
    participant C as ComparisonAgent
    participant T as SpecComparatorTool
    U->>SV: Chọn ≥ 2 sản phẩm → "Nhờ AI so sánh"
    SV->>APP: onCompare(products)
    APP->>APP: Ghi hoạt động "so sánh", chuyển sang tab Tư vấn
    APP->>V: ChatRequest kind = compare
    V->>V: Tạo hội thoại mới (tên = "So sánh giúp tôi: …")
    V->>API: POST /chat/compare (products)
    API->>C: compare(state)
    C->>T: run(products)
    T->>T: Chuẩn hóa nhãn thông số, chọn hàng có dữ liệu, tìm ô tốt nhất
    T-->>C: summary, table, markdown
    API-->>V: summary, table (không cào lại sàn)
    V-->>U: Bảng so sánh mở sẵn + nhận xét
```

## 9. Thẩm định link sản phẩm

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as SearchAssistantView
    participant G as AgentWorkflow
    participant O as Orchestrator
    participant LP as LinkParserAgent
    participant X as UrlExtractorTool
    participant M as Sàn TMĐT
    participant A as Advisor
    U->>V: Dán URL sản phẩm vào khung chat
    V->>G: POST /chat/stream
    G->>O: route(state)
    O->>O: Nhận dạng URL bằng biểu thức chính quy → intent parse_link
    G-->>V: status parsing_link
    G->>LP: parse(state)
    LP->>X: run(url)
    alt tiki.vn
        X->>M: GET /api/v2/products/{id}
    else thegioididong / dienmayxanh
        X->>M: Tải trang sản phẩm, đọc thông tin
    end
    M-->>X: Dữ liệu sản phẩm
    X-->>LP: ProductItemModel
    G-->>V: products (1 sản phẩm)
    G->>A: generate_response_stream (thẩm định giá, nơi bán, bảo hành)
    G-->>V: token … suggestions, done
```

## 10. Săn deal

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant G as AgentWorkflow
    participant M as SessionMemory
    participant S as EcomSearchTool
    participant D as DealFinderAgent
    participant C as ComparisonAgent
    participant A as Advisor
    U->>G: "Con nào đang giảm giá sâu nhất?" / "Săn deal tai nghe Sony"
    G->>G: route → intent find_deal
    G-->>U: status finding_deal
    alt Câu hỏi không nêu sản phẩm và có kết quả lượt trước
        G->>M: get_last_products(session)
        M-->>G: Sản phẩm lượt trước (không cào lại)
    else Có sản phẩm cụ thể
        G->>S: _run_search (cache → RAG → cào, có nới lỏng)
        S-->>G: Sản phẩm
    end
    G->>D: find_deals(state)
    D->>D: Xếp theo mức giảm, tính số tiền tiết kiệm, ghi search_notes
    G-->>U: products
    G->>C: compare (≥ 2 sản phẩm)
    G-->>U: comparison
    G->>A: generate_response_stream
    G-->>U: token … done
```

## 11. Tạo và chuyển hội thoại

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant L as ConversationList
    participant V as SearchAssistantView
    participant SS as useSyncedState(conversations)
    participant API as Backend
    U->>L: Bấm "+"
    L->>V: handleCreateConversation → activeId = null (màn hình chào)
    U->>V: Gửi câu hỏi đầu tiên
    V->>V: createConversation(id mới, tên = câu hỏi, ≤ 80 ký tự)
    V->>SS: Thêm hội thoại (tối đa 30)
    SS->>API: PUT /auth/me/data/conversations (sau 0,8 giây)
    V->>API: POST /chat/stream (session_id = id mới)
    API->>API: claim_session → chat_sessions.user_id = người dùng
    U->>L: Chọn hội thoại khác
    alt Agent đang trả lời
        L-->>U: Bị khóa (mờ, không chọn được)
    else
        L->>V: activeId = id (lưu localStorage theo tài khoản)
        V-->>U: Hiện tin nhắn, câu hỏi làm rõ còn dở (nếu có)
    end
```

## 12. Lưu sản phẩm và đồng bộ dữ liệu cá nhân

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant C as ProductCard
    participant APP as ShoppingApp
    participant SS as useSyncedState
    participant LS as localStorage
    participant API as Auth API (user data)
    participant DB as user_data
    U->>C: "Lưu sản phẩm"
    C->>APP: handleToggleSave(product, query)
    APP->>SS: setSaved([...]) và ghi hoạt động "Lưu sản phẩm"
    SS->>LS: Lưu bản trên máy (shopping-ai.u.userId.saved-products)
    SS->>SS: Chờ 0,8 giây (gộp thay đổi liên tiếp)
    SS->>API: PUT /auth/me/data/saved-products
    API->>API: Kiểm tra khóa hợp lệ, kích thước ≤ 2 MB
    API->>DB: set_data(user_id, key, value)
    Note over U,DB: Đăng nhập trên thiết bị khác → GET /auth/me/data/saved-products trả đúng danh sách này
```

## 13. Tạo yêu cầu theo dõi giá — `POST /api/alerts`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant C as ProductCard
    participant TM as TrackPriceModal
    participant PA as usePriceAlerts
    participant API as Alerts API
    participant PR as ProductRepository
    participant AR as AlertRepository
    U->>C: "Theo dõi giá"
    C->>TM: Mở hộp thoại (sản phẩm)
    TM->>API: GET /products/{id}/history
    API-->>TM: Các mốc giá (biểu đồ)
    U->>TM: Chọn −10% hoặc nhập giá → "Theo dõi giá"
    TM->>TM: Kiểm tra 0 < giá mong muốn < giá hiện tại
    TM->>PA: create(product, target)
    PA->>API: POST /alerts
    API->>API: target_price ≥ giá hiện tại thì 400
    API->>PR: get_product_by_id
    alt Sản phẩm chưa có trong kho
        API->>PR: upsert_products (mốc giá đầu tiên)
    end
    API->>AR: create(user_id, user_email, target, initial = last = lowest = giá hiện tại, watching)
    API-->>PA: PriceAlert
    PA-->>U: Nút đổi thành "Đang theo dõi giá", ghi hoạt động "Theo dõi giá"
```

## 14. Xem lịch sử giá — `GET /api/products/{id}/history`

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as PriceAlertsView / TrackPriceModal
    participant API as Products API
    participant PR as ProductRepository
    participant CH as PriceHistoryChart
    U->>V: "Lịch sử giá"
    V->>API: GET /products/{id}/history (Bearer)
    API->>PR: get_price_history(id)
    PR-->>API: Mốc giá sắp theo recorded_at tăng dần
    API-->>V: productId, total, history
    V->>CH: points, targetPrice
    alt Ít hơn 2 mốc
        CH-->>U: "Mới có 1 mốc giá… biểu đồ sẽ hiện khi giá thay đổi"
    else
        CH-->>U: Đường bậc thang, đường đứt nét giá mong muốn, tooltip, nút "Xem bảng"
    end
```

## 15. Tra cứu chính sách bảo hành & đổi trả

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant V as PolicyLookupView
    participant SVC as shoppingService
    participant APP as ShoppingApp
    U->>V: Nhập sản phẩm / ngành hàng, chọn các sàn
    V->>SVC: runPolicyLookup(query, platformIds)
    SVC-->>V: Các bước tiến trình (mô phỏng trên giao diện)
    SVC->>SVC: Lọc PLATFORM_POLICIES theo sàn đã chọn, tìm sàn có thời hạn đổi trả dài nhất
    SVC-->>V: policies, summary
    V->>APP: onLookup → ghi hoạt động "Tra cứu chính sách"
    V-->>U: Bảng so sánh chính sách
    Note over SVC: Dữ liệu tham khảo trong frontend, chưa gọi backend (nợ kỹ thuật TD-03)
```

## 16. Thu thập dữ liệu hàng loạt — `POST /api/crawler/trigger`

```mermaid
sequenceDiagram
    actor A as Quản trị viên
    participant P as DataWarehousePanel
    participant API as Crawler API
    participant B as BatchCrawler
    participant S as EcomSearchTool
    participant DB as SQLite + ChromaDB
    A->>P: Mở Cài đặt → "Thu thập lại dữ liệu ngay"
    P->>API: POST /crawler/trigger (background = true)
    API->>API: require_admin (người dùng thường nhận 403)
    alt Đang có đợt thu thập
        API-->>P: already_running
    else
        API->>B: run_batch_crawl (tác vụ nền)
        API-->>P: started
        loop 8 từ khóa phổ biến, cách nhau 1,5 giây
            B->>S: run(query, platform, force_refresh)
            S->>DB: Lưu sản phẩm, mốc giá, vector
        end
        B->>B: last_run_stats (số sản phẩm, thời gian)
    end
    loop Mỗi 3 giây khi isRunning
        P->>API: GET /crawler/status
        API-->>P: Số sản phẩm, cập nhật gần nhất, isRunning
    end
```

## 17. Quy ước lỗi chung

`401` thiếu / sai token · `403` sai vai trò hoặc không sở hữu hội thoại · `404` không tìm thấy (kể cả không sở hữu yêu cầu theo dõi giá) · `422` dữ liệu không hợp lệ · lỗi trong stream gửi sự kiện `error`.
