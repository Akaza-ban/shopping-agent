# C4 mức 4 — Mã của hai luồng cốt lõi

## L4.1 Tư vấn mua sắm

```mermaid
classDiagram
    direction LR
    class ShopAIAgentWorkflow {
        -graph: CompiledStateGraph
        +execute(state) AgentState
        +execute_stream(state) AsyncIterator
        -_node_route(state)
        -_node_clarify(state)
        -_node_search(state)
        -_node_deal(state)
        -_node_compare(state)
        -_node_respond(state)
        -_node_finalize(state)
        -_run_search(state)
        -_relaxation_steps(criteria)
        -_maybe_ask_clarification(state)
        -_apply_pending_clarification(state)
    }
    class OrchestratorAgent {
        +route(state) AgentState
        -_fallback_route(state) AgentState
    }
    class EcomSearchTool {
        +run(query, category, criteria, platform, limit, force_refresh, notes) list
        +optimize_crawler_query(query, criteria) str
        +parse_mwg_listing(html, platform) list
        -_finalize(products, criteria, notes, limit)
    }
    class ProductEnricher {
        +enrich(products, max_items) list
        +fetch_current_price(product) dict
    }
    class product_ranker {
        <<module>>
        +rank_products(products, criteria) tuple
        +score_product(product, criteria) tuple
        +verifiable_attributes(criteria) dict
    }
    class ComparisonAgent {
        +compare(state) AgentState
    }
    class ShoppingAdvisorAgent {
        +build_standardized_context(state) dict
        +generate_response_stream(state) AsyncIterator
    }
    class SessionMemoryManager {
        +load_session_from_db(id)
        +save_turn(...)
        +get_conversation_state(id) dict
        +update_conversation_state(id, changes)
        +delete_session(id)
    }
    ShopAIAgentWorkflow *-- OrchestratorAgent
    ShopAIAgentWorkflow *-- EcomSearchTool
    ShopAIAgentWorkflow *-- ComparisonAgent
    ShopAIAgentWorkflow *-- ShoppingAdvisorAgent
    ShopAIAgentWorkflow ..> SessionMemoryManager
    EcomSearchTool ..> ProductEnricher
    EcomSearchTool ..> product_ranker
```

## L4.2 Theo dõi giá

```mermaid
classDiagram
    direction LR
    class AlertsRouter {
        <<FastAPI router>>
        +create_price_alert(req, user)
        +list_price_alerts(user)
        +delete_price_alert(id, user)
        +check_price_alerts(req, user)
    }
    class PriceWatcherService {
        +interval: int
        +start()
        +check_alerts(alert_ids, user_id) list
        -_check_one(alert)
        +get_audit_metrics() list
    }
    class guardrails {
        <<module>>
        +check_price(price, category) PriceVerdict
        +check_change(price, reference) PriceVerdict
        +same_price(a, b) bool
        +is_big_drop(price, reference) bool
    }
    class AlertRepository {
        +create(data) dict
        +list(status, user_id) list
        +update(id, fields) dict
        +delete(id, user_id) bool
    }
    class ProductRepository {
        +upsert_products(products) list
        +get_price_history(id) list
        +get_product_by_id(id) dict
    }
    class ProductEnricher {
        +fetch_current_price(product) dict
    }
    AlertsRouter ..> PriceWatcherService
    AlertsRouter ..> AlertRepository
    AlertsRouter ..> ProductRepository
    PriceWatcherService ..> guardrails
    AlertsRouter ..> guardrails
    PriceWatcherService ..> AlertRepository
    PriceWatcherService ..> ProductRepository
    PriceWatcherService ..> ProductEnricher
```

## Quy tắc chung cho cả hai luồng

- Node / dịch vụ không ném lỗi của hệ thống ngoài ra ngoài; ghi vào `search_notes` hoặc `last_note`.
- Mọi truy vấn dữ liệu cá nhân lọc theo `user_id` của người gọi.
- Trạng thái một lượt tư vấn nằm trong `AgentState`; trạng thái bền nằm trong SQLite (`conversation_states`, `price_alerts`). Singleton `session_memory` chỉ là bộ nhớ đệm RAM của các bảng hội thoại (lý do chỉ chạy một worker).

Chi tiết lớp và trình tự: [UML](../uml/README.md).
