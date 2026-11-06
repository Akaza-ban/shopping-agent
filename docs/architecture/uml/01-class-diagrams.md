# Biểu đồ lớp

## 1. Trạng thái agent (`backend/core/state.py`)

```mermaid
classDiagram
    class AgentState {
        +session_id: str
        +user_query: str
        +intent: Intent
        +criteria: UniversalSearchCriteria
        +messages: List~MessageItem~
        +found_products: List~ProductItemModel~
        +recommended_product: ProductItemModel
        +comparison_summary: str
        +comparison_table: dict
        +comparison_markdown: str
        +clarification: dict
        +search_notes: List~str~
        +relaxed_search: str
        +platform_filter: str
        +final_response: str
        +suggested_questions: List~str~
    }
    class UniversalSearchCriteria {
        +category: str
        +product_type: str
        +target_entity: str
        +is_accessory: bool
        +min_price: float
        +max_price: float
        +brands: List~str~
        +usage_purpose: str
        +priority: str
        +target_platforms: List~str~
        +attributes: dict
        +cleaned_query: str
    }
    class ProductItemModel {
        +id: str
        +name: str
        +platform: tgdd|dmx|tiki
        +platformName: str
        +currentPrice: float
        +originalPrice: float
        +discountPercent: int
        +rating: float
        +reviewsCount: str
        +specs: dict
        +warranty: str
        +returnPolicy: str
        +aiMatchScore: int
        +matchReasons: List~str~
        +attributeMatch: dict
        +detailFetched: bool
        +updatedAt: str
        +externalUrl: str
    }
    class MessageItem {
        +id: str
        +sender: user|ai
        +text: str
        +timestamp: str
    }
    AgentState *-- UniversalSearchCriteria
    AgentState *-- "0..*" ProductItemModel
    AgentState *-- "0..*" MessageItem
```

## 2. Tài khoản và xác thực

```mermaid
classDiagram
    class UserModel {
        +id: str
        +email: str
        +display_name: str
        +password_hash: str
        +role: user|admin
        +created_at: datetime
        +last_login_at: datetime
    }
    class AuthTokenModel {
        +token_hash: str
        +user_id: str
        +expires_at: datetime
    }
    class UserDataModel {
        +user_id: str
        +key: str
        +value_json: str
    }
    class UserRepository {
        +create_user(email, name, hash, role) UserModel
        +get_by_email(email) UserModel
        +create_token(user_id, token_hash, ttl)
        +get_user_by_token(token_hash) UserModel
        +delete_token(token_hash)
        +delete_user_tokens(user_id, keep)
        +get_data(user_id, key)
        +set_data(user_id, key, value)
    }
    class auth_service {
        <<module>>
        +validate_registration(email, password, name) List~str~
        +hash_password(pw) str
        +verify_password(pw, hash) bool
        +new_token() tuple
        +hash_token(token) str
    }
    class LoginThrottle {
        +locked_for(email) int
        +record_failure(email)
        +reset(email)
    }
    UserModel "1" -- "0..*" AuthTokenModel
    UserModel "1" -- "0..*" UserDataModel
    UserRepository ..> UserModel
    UserRepository ..> AuthTokenModel
    UserRepository ..> UserDataModel
```

## 3. Theo dõi giá

```mermaid
classDiagram
    class AlertModel {
        +id: str
        +user_id: str
        +product_id: str
        +product_name: str
        +target_price: float
        +initial_price: float
        +last_price: float
        +lowest_price: float
        +status: watching|triggered
        +last_checked_at: datetime
        +triggered_at: datetime
        +last_note: str
    }
    class PriceWatcherService {
        +interval: int
        +check_alerts(alert_ids, user_id) list
        -_check_one(alert)
    }
    class guardrails {
        <<module>>
        +check_price(price, category) PriceVerdict
        +check_change(price, reference) PriceVerdict
        +screen_products(products, references) tuple
        +same_price(a, b) bool
        +is_big_drop(price, reference) bool
    }
    class PriceVerdict {
        +ok: bool
        +rule: str
        +reason: str
    }
    PriceWatcherService ..> guardrails
    guardrails ..> PriceVerdict
    PriceWatcherService ..> AlertModel
```

## 4. Frontend (`frontend/src`)

```mermaid
classDiagram
    class AuthProvider {
        +status: loading|anonymous|authenticated
        +user: AuthUser
        +login(email, password)
        +register(email, password, name)
        +logout()
    }
    class agentApi {
        <<module>>
        +apiFetch(path, init) Response
        +streamChat(sessionId, message, handlers)
        +compareProducts(sessionId, products)
        +createAlert(product, target)
        +getPriceHistory(productId)
        +getUserData(key) / putUserData(key, value)
    }
    class useSyncedState {
        <<hook>>
        +(userId, key, initial) [value, setValue]
    }
    class ShoppingApp {
        +userId
        +history, saved, activities
    }
    class SearchAssistantView {
        +conversations
        +handleSendQuery(text)
    }
    AuthProvider ..> agentApi
    ShoppingApp ..> useSyncedState
    SearchAssistantView ..> useSyncedState
    SearchAssistantView ..> agentApi
    useSyncedState ..> agentApi
```

## 5. Quy ước DTO

- Dữ liệu sản phẩm / theo dõi giá trả về `camelCase` (`currentPrice`, `targetPrice`).
- Body yêu cầu dùng `snake_case` (`target_price`, `display_name`, `session_id`).
- Lỗi luôn `{"detail": str}`.
