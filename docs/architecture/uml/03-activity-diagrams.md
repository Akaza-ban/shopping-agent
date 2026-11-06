# Biểu đồ hoạt động

## 1. Quy trình nghiệp vụ mua sắm có trợ lý AI

Ba làn: Người dùng, Trợ lý AI, Sàn TMĐT. Trợ lý chỉ cào sàn khi kho dữ liệu không có kết quả phù hợp.

```mermaid
flowchart TB
    subgraph user["Người dùng"]
        u1(["Bắt đầu"]) --> u2["Mô tả nhu cầu bằng ngôn ngữ tự nhiên"]
        u3["Chọn / nhập ngân sách"]
        u4["Xem đề xuất, bảng so sánh, lưu ý dữ liệu"]
        u5{"Hài lòng?"}
        u6["Lưu sản phẩm / theo dõi giá / mở trang sàn"]
        u7(["Kết thúc"])
    end
    subgraph agent["Trợ lý AI"]
        a1["Phân loại ý định, trích tiêu chí (LLM)"]
        a2{"Yêu cầu còn chung chung?"}
        a3["Hỏi làm rõ ngân sách"]
        a4["Gộp câu trả lời vào tiêu chí"]
        a5{"Kho dữ liệu có kết quả?"}
        a6["Lọc ngữ nghĩa"]
        a7["Đọc trang chi tiết, đối chiếu thông số, xếp hạng"]
        a8{"Có sản phẩm đạt?"}
        a9["Nới lỏng tiêu chí / tìm thêm ngoài ngân sách"]
        a10["Lập bảng so sánh, soạn lời tư vấn"]
    end
    subgraph shop["Sàn TMĐT"]
        s1["Trả danh sách sản phẩm (Tiki, TGDĐ, ĐMX)"]
        s2["Trả trang chi tiết: thông số, bảo hành, đổi trả"]
    end
    u2 --> a1 --> a2
    a2 -- "có" --> a3 --> u3 --> a4 --> a5
    a2 -- "không" --> a5
    a5 -- "có" --> a7
    a5 -- "không" --> s1 --> a6 --> a7
    a7 <--> s2
    a7 --> a8
    a8 -- "không" --> a9 --> a5
    a8 -- "có" --> a10 --> u4 --> u5
    u5 -- "chưa, hỏi tiếp" --> u2
    u5 -- "có" --> u6 --> u7
```

## 2. UC05 — Tư vấn mua sắm (một lượt)

```mermaid
flowchart TB
    start(["Người dùng gửi câu hỏi"]) --> own{"Hội thoại thuộc người dùng?"}
    own -- "không" --> e403(["403"])
    own -- "có / mới" --> load["Nạp trí nhớ phiên: lịch sử, sản phẩm lượt trước, câu hỏi làm rõ đang chờ"]
    load --> route["Router LLM: ý định + tiêu chí (lỗi thì phân loại từ khóa)"]
    route --> pend{"Có câu hỏi làm rõ đang chờ?"}
    pend -- "có" --> merge["Gộp câu trả lời vào tiêu chí đã lưu"] --> intent
    pend -- "không" --> intent{"Ý định"}
    intent -- "parse_link" --> link["Bóc tách link"] --> respond
    intent -- "general_advice / out_of_scope" --> respond
    intent -- "find_deal" --> deal["Săn deal: dùng lại sản phẩm lượt trước hoặc tìm kiếm"] --> compare
    intent -- "search / compare" --> broad{"Thiếu giá, hãng, model và chưa hỏi ngành này?"}
    broad -- "có" --> ask["Gửi câu hỏi làm rõ"] --> fin
    broad -- "không" --> search["Cache SQLite → ChromaDB → cào song song"]
    search --> enrich["Làm giàu trang chi tiết, đối chiếu thông số, xếp hạng"]
    enrich --> empty{"Không có sản phẩm?"}
    empty -- "đúng" --> relax["Bỏ thông số → +20% ngân sách → bỏ hãng"] --> search
    empty -- "sai" --> verified{"Có thông số bắt buộc mà không sản phẩm nào đúng?"}
    verified -- "đúng" --> upsell["Tìm thêm tới +20% ngân sách, ghi chú"] --> compare
    verified -- "sai" --> compare{"≥ 2 sản phẩm?"}
    compare -- "có" --> table["Tool so sánh dựng bảng"] --> respond
    compare -- "không" --> respond["Advisor stream lời tư vấn + lưu ý dữ liệu"]
    respond --> fin["Lưu lượt hội thoại, gợi ý câu hỏi tiếp theo"]
    fin --> done(["Kết thúc lượt"])
```

## 3. Khởi động ứng dụng và cổng đăng nhập (UC01–UC03)

```mermaid
flowchart TB
    open(["Mở ứng dụng"]) --> theme["Áp chế độ sáng / tối từ lựa chọn đã lưu"]
    theme --> tok{"Có token trong trình duyệt?"}
    tok -- "không" --> auth["Màn hình Đăng nhập / Đăng ký"]
    tok -- "có" --> me["GET /auth/me"]
    me -- "200" --> app["Dựng ứng dụng cho tài khoản này"]
    me -- "401" --> clear["Xóa token"] --> auth
    auth --> mode{"Thẻ đang chọn"}
    mode -- "Đăng ký" --> reg["Kiểm tra tại chỗ → POST /auth/register"]
    mode -- "Đăng nhập" --> login["POST /auth/login"]
    reg -- "201" --> app
    reg -- "409 / 422" --> auth
    login -- "200" --> app
    login -- "401 / 429" --> auth
    app --> sync["Tải dữ liệu cá nhân (hội thoại, đã lưu, lịch sử) từ máy chủ, chuyển dữ liệu cũ nếu tài khoản chưa có"]
    sync --> use["Sử dụng"]
    use -- "Đăng xuất hoặc 401 ở bất kỳ lời gọi nào" --> auth
```

## 4. Tổng quan, lịch sử hoạt động, góp ý (UC15, UC18)

```mermaid
flowchart TB
    act(["Người dùng thao tác"]) --> kind{"Loại thao tác"}
    kind -- "Tìm kiếm có kết quả" --> h1["Thêm vào tìm kiếm gần đây (tối đa 20)"] --> log
    kind -- "Lưu / bỏ lưu, so sánh, theo dõi giá, tra cứu chính sách, đổi nguồn dữ liệu" --> log
    kind -- "Gửi góp ý / yêu cầu hỗ trợ" --> fb["Chọn chủ đề, nhập nội dung (liên hệ nếu là hỗ trợ)"] --> log
    kind -- "Giá đạt mức mong muốn (vòng tải danh sách 5 phút)" --> log
    log["Ghi hoạt động (tối đa 200)"] --> sync["useSyncedState: lưu trên máy + PUT /auth/me/data/activities sau 0,8 giây"]
    sync --> views{"Màn hình"}
    views -- "Tổng quan" --> dash["5 ô thống kê, tìm kiếm & đã lưu gần đây"]
    views -- "Lịch sử hoạt động" --> list["Nhóm theo ngày, lọc theo loại"]
    list --> reopen{"Mở lại?"}
    reopen -- "có" --> chat["Tạo hội thoại mới hiển thị lại kết quả"]
    reopen -- "Xóa lịch sử" --> wipe["Danh sách rỗng, đồng bộ lên máy chủ"]
```
