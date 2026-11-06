# ShopAI Multi-Agent Backend System

Hệ thống Backend AI Agent chuyên biệt phục vụ cho ứng dụng thương mại điện tử thông minh **ShopAI** (Frontend nằm ở thư mục `../G`).

## 🌟 Tính Năng Của Hệ Thống Agent

1. **Orchestrator Agent**: Phân tích câu hỏi người dùng, quyết định kích hoạt Agent phù hợp (Tìm kiếm, So sánh, Bóc tách link hay Tư vấn).
2. **Shopping Advisor Agent**: Đàm thoại, tư vấn lựa chọn sản phẩm dựa trên nhu cầu sử dụng và ngân sách.
3. **Comparison Agent**: Phân tích sự chênh lệch giá, cấu hình, chính sách bảo hành giữa các sàn (Shopee, Lazada, Tiki).
4. **Link Parser Agent**: Đọc URL sản phẩm từ người dùng dán vào, trích xuất tự động thông số kỹ thuật, giá và hình ảnh.
5. **Deal Finder Agent**: Tìm kiếm voucher, mã khuyến mãi và gợi ý thời điểm mua tốt nhất.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### 1. Tạo môi trường ảo Python
```bash
# Tại thư mục B:
python -m venv venv

# Kích hoạt trên Windows:
.\venv\Scripts\activate
# Hoặc trên Linux/macOS:
source venv/bin/activate
```

### 2. Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` từ `.env.example`:
```bash
copy .env.example .env
```
Điền `GEMINI_API_KEY` của bạn vào file `.env`.

### 4. Khởi chạy máy chủ FastAPI
```bash
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger UI): `http://localhost:8000/docs`
- Kết nối tới Frontend: Frontend `G` gọi tới `http://localhost:8000/api/v1/...`
