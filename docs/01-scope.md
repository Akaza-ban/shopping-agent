# Phạm vi V1

> Trạng thái thiết kế: V1
>
> Trạng thái triển khai: ĐÃ CHẠY ĐƯỢC — backend FastAPI + LangGraph và frontend React đã nối với nhau, dữ liệu thật từ các sàn

Tên sản phẩm trên giao diện: **Shopping AI** (trợ lý mua sắm thông minh).

## Vấn đề

Người mua đồ công nghệ, điện máy tại Việt Nam muốn:

- mô tả nhu cầu bằng ngôn ngữ tự nhiên (ngân sách, cấu hình, mục đích) thay vì tự lọc trên từng sàn;
- biết sản phẩm nào **thật sự** đáp ứng thông số bắt buộc (ví dụ GPU RTX 4070), vì tên sản phẩm trên trang danh sách thường không ghi đủ;
- so sánh giá, cấu hình, bảo hành, đổi trả giữa các nơi bán trong một bảng;
- được báo khi giá giảm tới mức mong muốn;
- tra cứu chính sách bảo hành, đổi trả của các nền tảng.

Đây **không** phải một sàn thương mại điện tử, không đặt hàng, không thanh toán, và không phải chatbot trả lời tự do: mọi giá và thông số trình bày cho người dùng phải lấy từ dữ liệu đã thu thập.

## Mục tiêu V1

V1 hỗ trợ:

- Đăng ký, đăng nhập, đăng xuất, đổi tên hiển thị và mật khẩu; phân quyền người dùng / quản trị viên ở backend.
- Tư vấn mua sắm qua hội thoại nhiều lượt, stream từng bước tiến trình (Server-Sent Events).
- Hỏi làm rõ ngân sách khi yêu cầu còn quá chung; gộp câu trả lời vào tiêu chí.
- Thu thập sản phẩm từ Tiki, Thế Giới Di Động, Điện Máy Xanh (cache SQLite → RAG ChromaDB → cào trực tiếp).
- Đọc trang chi tiết để lấy thông số, bảo hành, đổi trả; đối chiếu thông số bắt buộc.
- Xếp hạng có giải thích lý do; tự nới lỏng tiêu chí khi không có kết quả; tìm thêm ngoài ngân sách khi không có sản phẩm đúng cấu hình.
- Bảng so sánh có cấu trúc ngay trong khung chat (so sánh là công cụ của agent, không phải màn hình riêng).
- Săn deal, thẩm định link sản phẩm.
- Quản lý hội thoại (tạo, chuyển, xóa); tên hội thoại là câu hỏi đầu tiên.
- Lưu sản phẩm; nhờ AI so sánh sản phẩm đã lưu.
- Theo dõi giá: đọc giá thật định kỳ, báo khi đạt giá mong muốn, lịch sử giá.
- Tổng quan, lịch sử hoạt động, góp ý / yêu cầu hỗ trợ, giao diện sáng / tối.
- Dữ liệu cá nhân (hội thoại, sản phẩm đã lưu, lịch sử) đồng bộ theo tài khoản.

## Ngoài phạm vi (Non-goals)

V1 **không** gồm:

- Đặt hàng, giỏ hàng, thanh toán, mã giảm giá riêng của người dùng.
- Shopee, Lazada: đã bỏ khỏi hệ thống vì cơ chế chống bot (không cào, không đọc link).
- Gửi email / thông báo đẩy khi đạt giá (trạng thái chỉ hiện trong ứng dụng).
- Đăng nhập bằng Google/Facebook, xác thực hai lớp, quên mật khẩu qua email, refresh token.
- Quản lý người dùng bởi quản trị viên (khóa / mở khóa tài khoản).
- Thu thập tự động chính sách đổi trả (màn tra cứu chính sách dùng dữ liệu tham khảo).

## Hiện trạng

| Thành phần | Thực tế |
|---|---|
| Frontend | React 19 + Vite + Tailwind 4 (`frontend/`). Gọi API thật qua `src/services/agentApi.ts`; riêng dữ liệu chính sách đổi trả là dữ liệu tham khảo trong `shoppingService.ts`. |
| Backend | FastAPI + LangGraph (`backend/`). 29 operation REST/SSE (xem [OpenAPI](api/openapi.json)). |
| Cơ sở dữ liệu | SQLite (`backend/shopai.db`, SQLAlchemy async) + ChromaDB (`backend/chroma_db/`). Bảng tạo tự động khi khởi động. |
| LLM | DeepSeek → OpenRouter → Groq (chuỗi dự phòng, giao diện tương thích OpenAI). |
| Xác thực | Token Bearer ngẫu nhiên, DB lưu SHA-256; mật khẩu bcrypt. |
| Kiểm thử | 147 test pytest (`backend/tests/`); kiểm thử đầu-cuối bằng trình duyệt headless. |

## Kiến trúc V1

```text
Trình duyệt (React SPA)
    → REST / SSE (JSON, Bearer token)
FastAPI
    → Đồ thị LangGraph (agent + công cụ)
        → Dịch vụ LLM (DeepSeek / OpenRouter / Groq)
        → Sàn TMĐT (Tiki API, trang Thế Giới Di Động / Điện Máy Xanh)
    → SQLite (sản phẩm, lịch sử giá, hội thoại, tài khoản, theo dõi giá)
    → ChromaDB (tìm kiếm ngữ nghĩa)
```

Chi tiết: [arc42](architecture/arc42/README.md), [C4](architecture/c4/README.md).
