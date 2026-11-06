# _legacy

Mã cũ không còn được dùng, giữ lại tạm thời để tham khảo (dự án chưa có git). Có thể xóa cả thư mục này.

- `app/`: bản trùng của `src/` (thiếu router `crawler`, import `..config.settings` bị hỏng).
- `config/`: cấu hình Gemini cũ (`GEMINI_API_KEY`), không module nào import.
- `config.py`: file re-export `src.config`, bị package `config/` che khuất nên không bao giờ được nạp.

Cấu hình duy nhất hiện tại: `src/config.py`. Điểm chạy server: `uvicorn src.main:app`.
