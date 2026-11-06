# Sơ đồ dữ liệu

> Nguồn: `backend/database/models/*.py`. Mô tả cột và quy tắc: [05-data-model.md](05-data-model.md).

## Quan hệ giữa các bảng

```mermaid
erDiagram
    users ||--o{ auth_tokens : "có phiên"
    users ||--o{ user_data : "có dữ liệu"
    users ||--o{ chat_sessions : "sở hữu"
    users ||--o{ price_alerts : "sở hữu"
    chat_sessions ||--o{ chat_messages : "gồm"
    chat_sessions ||--o| conversation_states : "trạng thái"
    products ||--o{ price_history : "mốc giá"
    products ||--o{ price_alerts : "được theo dõi"
    price_alerts ||--o{ price_checks : "nhật ký kiểm tra"
    search_cache }o..o{ products : "product_ids (JSON)"

    users {
        string id PK
        string email UK
        string display_name
        string password_hash
        string role
        datetime created_at
        datetime last_login_at
    }
    auth_tokens {
        string token_hash PK
        string user_id FK
        datetime created_at
        datetime expires_at
    }
    user_data {
        int id PK
        string user_id FK
        string key
        text value_json
        datetime updated_at
    }
    chat_sessions {
        string id PK
        string user_id
        string title
        text summary
        datetime created_at
    }
    chat_messages {
        string id PK
        string session_id
        string sender
        text text
        text products_json
        text criteria_json
        datetime created_at
    }
    conversation_states {
        string session_id PK
        text state_json
        datetime updated_at
    }
    products {
        string id PK
        string name
        string category
        string platform
        float original_price
        float current_price
        int discount_percent
        float rating
        text specs
        string warranty
        string external_url
        string source_category_path
        datetime updated_at
    }
    price_history {
        int id PK
        string product_id FK
        float price
        float original_price
        int discount_percent
        datetime recorded_at
    }
    price_alerts {
        string id PK
        string user_id
        string product_id
        float target_price
        float last_price
        float lowest_price
        string status
        datetime last_checked_at
        datetime triggered_at
        float pending_price
        datetime pending_at
        bool in_stock
    }
    price_checks {
        int id PK
        string alert_id
        string user_id
        float price
        bool in_stock
        string outcome
        text note
        float latency_ms
        datetime checked_at
    }
    search_cache {
        int id PK
        string query
        string platform
        text product_ids
        datetime expires_at
    }
```

## Giá trị liệt kê

| Cột | Giá trị |
|---|---|
| `users.role` | `user`, `admin` |
| `price_alerts.status` | `watching`, `triggered` |
| `chat_messages.sender` | `user`, `ai` |
| `products.platform` | `tgdd`, `dmx`, `tiki` |
| `user_data.key` | `conversations`, `saved-products`, `activities`, `search-history` |

## Ràng buộc bảo mật

- `auth_tokens` chỉ chứa SHA-256 của token; lộ CSDL không lộ token dùng được.
- `chat_sessions.user_id` và `price_alerts.user_id` được kiểm tra ở mọi API đọc / ghi.
- Khóa ngoại khai báo `ON DELETE CASCADE` (`auth_tokens`, `user_data`, `price_history`), nhưng SQLite chỉ thực thi khi bật `PRAGMA foreign_keys` (hiện chưa bật). V1 chưa có chức năng xóa tài khoản hay sản phẩm; xóa hội thoại thì `ChatRepository.clear_session` xóa tường minh tin nhắn và trạng thái của phiên.
