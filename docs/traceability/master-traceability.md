# Ma trận truy vết — Shopping AI V1

> Trạng thái: V1 — cột "Kiểm chứng" dẫn tới test thật trong `backend/tests/` (đạt ngày 29/10/2026) hoặc E2E

## Truy vết chức năng

| Yêu cầu | Use case | Tiêu chí | Màn hình | Thành phần (C3) | API | Bảng dữ liệu | Kiểm chứng |
|---|---|---|---|---|---|---|---|
| US01 | UC01 | AC-UC01 | SCR-01 | Auth | `POST /auth/register` | `users`, `auth_tokens` | `test_auth::test_register_validation_and_duplicate`, E2E 2–3 |
| US02 | UC02 | AC-UC02 | SCR-01 | Auth | `POST /auth/login` | `users`, `auth_tokens` | `test_auth::test_wrong_password_same_message_and_lockout`, E2E 7 |
| US03 | UC03 | AC-UC03 | Khung → SCR-01 | Auth | `POST /auth/logout` | `auth_tokens` | `test_auth::test_register_login_me_logout`, E2E 6 |
| US04 | UC04 | AC-UC04 | DLG-04 | Auth | `PATCH /auth/me`, `POST /auth/change-password` | `users`, `auth_tokens` | `test_auth::test_change_password_revokes_other_sessions` |
| US05 | UC05 | AC-UC05 | SCR-03 | Agent Workflow, Orchestrator, EcomSearch, Enricher, Ranker, Advisor | `POST /chat/stream`, `POST /chat` | `products`, `price_history`, `search_cache`, `chat_*` | `test_architecture_level3::*`, `test_advisor_level2::test_rank_*`, `test_search_level1::*` |
| US06 | UC06 | AC-UC06 | SCR-03 | Agent Workflow, Session Memory | `POST /chat/stream` (`clarification`) | `conversation_states` | `test_advisor_level2::test_clarification_asked_once_and_answer_merged`, `test_architecture_level3::test_pending_clarification_survives_restart` |
| US07 | UC07 | AC-UC07 | SCR-03, SCR-05 | Comparison | `comparison` (SSE), `POST /chat/compare` | — | `test_advisor_level2::test_comparison_table_marks_best_cells`, `test_architecture_level3::test_compare_endpoint_builds_table` |
| US08 | UC08 | AC-UC08 | SCR-03 | Orchestrator, LinkParser | `POST /parse-link`, chat | `products` | `test_agents::test_link_parser_intent` |
| US09 | UC09 | AC-UC09 | SCR-03 | DealFinder | `POST /chat/stream` | `chat_messages` | `test_architecture_level3::test_deal_*` |
| US10 | UC10 | AC-UC10 | SCR-03 | Session Memory, Chat API | `DELETE /chat/history/{id}`, `/auth/me/data/conversations` | `chat_sessions`, `chat_messages`, `conversation_states`, `user_data` | `test_architecture_level3::test_delete_conversation_clears_memory_and_db`, `test_auth::test_conversations_are_private` |
| US11 | UC11 | AC-UC11 | SCR-05 | User Data | `/auth/me/data/saved-products` | `user_data` | `test_auth::test_user_data_sync`, E2E 8–9 |
| US12 | UC12 | AC-UC12 | SCR-06, DLG-01 | Price Watcher, Guardrails, Enricher | `/alerts`, `/alerts/check` | `price_alerts`, `price_history` | `test_price_alerts::*`, `test_auth::test_price_alerts_are_private` |
| US13 | UC13 | AC-UC13 | SCR-06, DLG-01 | Product Repository | `GET /products/{id}/history` | `price_history` | `test_cache_first_search::test_product_price_history_api`, `test_product_repository::test_upsert_price_change_tracking` |
| US14 | UC14 | AC-UC14 | SCR-04 | (frontend) | — | — | Thủ công |
| US15 | UC15 | AC-UC15 | SCR-02, SCR-07 | User Data | `/auth/me/data/{activities,search-history}` | `user_data` | E2E 8–9 |
| US16 | UC16 | AC-UC16 | DLG-02 | Batch Crawler | `/crawler/status`, `/crawler/trigger` | `products` | `test_auth::test_admin_only_crawler_trigger`, `test_batch_crawler::*` |
| US17 | UC17 | AC-UC17 | SCR-06 | Price Watcher | (vòng nền) | `price_alerts`, `price_history` | `test_price_alerts::*` |
| US18 | UC18 | AC-UC18 | DLG-03 | User Data | `/auth/me/data/activities` | `user_data` | E2E 4, 8 |

## Truy vết chất lượng / NFR

| NFR | Quy tắc | Thành phần | Kiểm chứng |
|---|---|---|---|
| NFR-01 | — | EcomSearch (cache-first) | `test_cache_first_search::test_cache_first_performance_boost` |
| NFR-04 | BR-005 | Advisor, `get_chat_model` | `test_shopping_advisor_full::test_step4_zero_crash_fallback_on_error` |
| NFR-05 | BR-008 | Session Memory | `test_architecture_level3::test_pending_clarification_survives_restart` |
| NFR-06 | BR-003, BR-004 | Auth | `test_auth.py` |
| NFR-07 | BR-002 | Auth, Chat API, Alerts API | `test_auth::test_*_private`, `test_user_data_sync` |
| NFR-10 | BR-010, BR-011 | Price Watcher, Guardrails | `test_price_alerts::test_watcher_triggers_and_records_history`, `test_guardrails::*` |
| NFR-11 | BR-009 | MWG parser | `test_search_level1::test_parse_tgdd_listing_2026`, `test_parse_dmx_listing_2026` |

## Tính nhất quán

- Mỗi US có đúng một UC và một AC cùng số.
- Mỗi API trong [openapi.json](../api/openapi.json) xuất hiện ít nhất một lần trong bảng trên hoặc trong [api/README.md](../api/README.md).
- Thay đổi API / lược đồ phải cập nhật bảng này cùng lúc.
