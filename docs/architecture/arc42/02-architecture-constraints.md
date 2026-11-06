# 2. Ràng buộc kiến trúc

## 2.1 Ràng buộc kỹ thuật

| Ràng buộc | Nội dung |
|---|---|
| Ngôn ngữ backend | Python 3.11 (đề tài yêu cầu Python, LLM, LangGraph, BeautifulSoup, FastAPI) |
| Điều phối agent | LangGraph `StateGraph` |
| LLM | API tương thích OpenAI (DeepSeek, OpenRouter, Groq) qua `langchain-openai` |
| Thu thập dữ liệu | `httpx` + BeautifulSoup; không có API chính thức của TGDĐ/ĐMX; Tiki dùng API JSON công khai |
| Lưu trữ | SQLite cục bộ (async) + ChromaDB nhúng; không cần máy chủ CSDL |
| Frontend | React SPA (Vite, TypeScript, Tailwind) chạy trên trình duyệt |
| Giao tiếp | REST JSON + Server-Sent Events |

## 2.2 Ràng buộc tổ chức

- Nhóm sinh viên, thời gian một học kỳ; ưu tiên chạy được trên máy cá nhân (Windows).
- Chi phí LLM trả theo lượt gọi: hạn chế số lần gọi mỗi lượt tư vấn (router, lọc ngữ nghĩa, advisor).
- Không có quyền / thỏa thuận với sàn: phải tôn trọng giới hạn truy cập, cache để giảm số lần cào.

## 2.3 Quy ước

- Thông báo lỗi, giao diện, chú thích mã bằng tiếng Việt.
- Thời gian lưu UTC; giá VND.
- Mọi bí mật trong `backend/.env`; không in khóa API ra log.
- Tài liệu Markdown + Mermaid trong `docs/`.

## 2.4 Ràng buộc nghiệp vụ

- Không đặt hàng, không thanh toán, không giữ thông tin thẻ.
- Không trình bày giá / thông số không có nguồn (BR-005).
- Dữ liệu của sàn có thể thay đổi bất kỳ lúc nào: luôn ghi độ mới dữ liệu khi lấy từ kho.
