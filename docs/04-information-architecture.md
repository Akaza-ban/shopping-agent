# Kiến trúc thông tin

> Trạng thái: V1 — đã triển khai trong `frontend/src`

## Phân quyền màn hình

| Màn hình | Khách | Người dùng | Quản trị viên |
|---|---|---|---|
| SCR-01 Đăng nhập / Đăng ký | ✓ | | |
| SCR-02 … SCR-07, DLG-01, DLG-03 … DLG-05 | | ✓ | ✓ |
| DLG-02 Nguồn & kho dữ liệu (mục "Cài đặt nguồn dữ liệu", nút "Nguồn dữ liệu" trên thanh tiêu đề) | | ẩn | ✓ |

> Bật / tắt nguồn dữ liệu là cấu hình hệ thống nên chỉ quản trị viên thấy (DLG-02); lựa chọn hiện vẫn chỉ lưu trên trình duyệt, chưa áp dụng ở máy chủ — xem [reviews/F13](reviews/F13-nguon-kho-du-lieu.md) phần A. Người dùng thường có hộp thoại **Cài đặt** (DLG-05) chỉ gồm thiết lập lõi: giao diện (sáng / tối / tự động theo giờ) và ngôn ngữ (Tiếng Việt / English), lưu theo tài khoản.

Chưa đăng nhập thì ứng dụng chỉ hiển thị SCR-01. Đăng xuất hoặc token hết hạn đưa về SCR-01.

## Danh sách màn hình

| ID | Màn hình | Component | Mục đích |
|---|---|---|---|
| SCR-01 | Đăng nhập / Đăng ký | `AuthView.tsx` | Hai thẻ Đăng nhập / Đăng ký, kiểm tra dữ liệu tại chỗ, ẩn/hiện mật khẩu |
| SCR-02 | Tổng quan | `DashboardView.tsx` | Thao tác nhanh, 5 ô thống kê, tìm kiếm & đã lưu gần đây |
| SCR-03 | Tư vấn mua sắm | `SearchAssistantView.tsx`, `ConversationList.tsx` | Danh sách hội thoại + khung chat, tiến trình agent, thẻ sản phẩm, bảng so sánh, câu hỏi làm rõ |
| SCR-04 | Tra cứu bảo hành & đổi trả | `PolicyLookupView.tsx` | So sánh chính sách giữa các sàn (dữ liệu tham khảo) |
| SCR-05 | Sản phẩm đã lưu | `SavedProductsView.tsx` | Danh sách đã lưu, chọn để so sánh, theo dõi giá |
| SCR-06 | Theo dõi giá | `PriceAlertsView.tsx` | Danh sách theo dõi, kiểm tra ngay, lịch sử giá |
| SCR-07 | Lịch sử hoạt động | `ActivityLogView.tsx` | Hoạt động theo ngày, lọc, mở lại trong chat |
| DLG-01 | Hộp thoại Theo dõi giá | `TrackPriceModal.tsx` | Chọn giá mong muốn, xem lịch sử giá |
| DLG-02 | Hộp thoại Nguồn & kho dữ liệu | `SettingsModal.tsx`, `DataWarehousePanel.tsx` | Bật/tắt nguồn, tình trạng kho, thu thập lại (admin) |
| DLG-03 | Hộp thoại Góp ý / Hỗ trợ | `HelpRequestModal.tsx` | Gửi góp ý, yêu cầu hỗ trợ |
| DLG-04 | Hộp thoại Tài khoản | `AccountModal.tsx` | Đổi tên hiển thị, đổi mật khẩu |
| DLG-05 | Hộp thoại Cài đặt | `PreferencesModal.tsx` | Giao diện (sáng / tối / tự động theo giờ), ngôn ngữ (Tiếng Việt / English) |

Khung ứng dụng (`App.tsx`): thanh bên (`Sidebar.tsx`, thu gọn được), thanh tiêu đề (`Header.tsx`: tên màn hình, nút nguồn dữ liệu, nút sáng/tối, menu tài khoản).

## Phân cấp màn hình

```mermaid
flowchart TB
    auth["SCR-01 Đăng nhập / Đăng ký"] -->|đăng nhập thành công| shell
    subgraph shell["Khung ứng dụng: thanh bên + thanh tiêu đề"]
        d["SCR-02 Tổng quan"]
        c["SCR-03 Tư vấn mua sắm"]
        p["SCR-04 Tra cứu chính sách"]
        s["SCR-05 Sản phẩm đã lưu"]
        a["SCR-06 Theo dõi giá"]
        h["SCR-07 Lịch sử hoạt động"]
    end
    c --> dlg1["DLG-01 Theo dõi giá"]
    s --> dlg1
    shell --> dlg2["DLG-02 Nguồn & kho dữ liệu"]
    shell --> dlg3["DLG-03 Góp ý / Hỗ trợ"]
    shell --> dlg4["DLG-04 Tài khoản"]
    shell --> dlg5["DLG-05 Cài đặt"]
    shell -->|đăng xuất / hết phiên| auth
```

## Luồng thao tác chính

```mermaid
flowchart LR
    q["Nhập nhu cầu"] --> clar{"Đủ thông tin?"}
    clar -- "chưa (thiếu ngân sách)" --> pick["Chọn ngân sách"] --> res
    clar -- "đủ" --> res["Thẻ sản phẩm + lý do + lưu ý dữ liệu"]
    res --> cmp["Bảng so sánh"]
    res --> save["Lưu sản phẩm"] --> savedv["SCR-05"] --> ai["Nhờ AI so sánh"]
    res --> track["Theo dõi giá"] --> alerts["SCR-06: kiểm tra giá, lịch sử giá"]
    res --> follow["Hỏi nối tiếp / câu hỏi gợi ý"] --> res
```

## Sơ đồ điều hướng (sitemap)

Mục trên thanh bên theo đúng thứ tự hiển thị, từ trái sang phải.

```mermaid
flowchart TB
    root(["Shopping AI"])
    root --> auth["SCR-01 Đăng nhập / Đăng ký"]
    root --> app["Khung ứng dụng"]

    app --> side["Thanh bên"]
    app --> head["Thanh tiêu đề"]

    side --> m1["1. Tổng quan<br/>SCR-02"]
    side --> m2["2. Tư vấn mua sắm<br/>SCR-03"]
    side --> m3["3. Tra cứu bảo hành và đổi trả<br/>SCR-04"]
    side --> m4["4. Sản phẩm đã lưu<br/>SCR-05"]
    side --> m5["5. Theo dõi giá<br/>SCR-06"]
    side --> m6["6. Lịch sử hoạt động<br/>SCR-07"]
    side --> help["Nhóm Trợ giúp và hỗ trợ"]
    help --> h1["Gửi góp ý → DLG-03"]
    help --> h2["Yêu cầu hỗ trợ → DLG-03"]
    help --> h3["Cài đặt → DLG-05"]
    help --> h4["Cài đặt nguồn dữ liệu → DLG-02<br/>(chỉ quản trị viên)"]

    head --> t1["Nút Nguồn dữ liệu: N nền tảng → DLG-02<br/>(chỉ quản trị viên)"]
    head --> t2["Nút sáng / tối"]
    head --> t3["Menu tài khoản"]
    t3 --> t31["Tài khoản và mật khẩu → DLG-04"]
    t3 --> t32["Đăng xuất → SCR-01"]

```

Liên kết chéo giữa các màn hình (nút, liên kết trong nội dung):

```mermaid
flowchart LR
    m1["SCR-02 Tổng quan"] -- "thao tác nhanh, tìm kiếm gần đây" --> m2["SCR-03 Tư vấn mua sắm"]
    m1 -- "Xem tất cả" --> m4["SCR-05 Sản phẩm đã lưu"]
    m4 -- "Nhờ AI so sánh" --> m2
    m6["SCR-07 Lịch sử hoạt động"] -- "Mở lại" --> m2
    m2 -- "Tra cứu chính sách" --> m3["SCR-04 Tra cứu bảo hành và đổi trả"]
    m2 -- "Theo dõi giá trên thẻ sản phẩm" --> dlg1["DLG-01 Theo dõi giá"]
    m4 -- "Theo dõi giá" --> dlg1
    dlg1 -- "tạo yêu cầu" --> m5["SCR-06 Theo dõi giá"]
    m2 -- "Xem tại sàn, Mở trang gốc" --> ext(["Trang sản phẩm trên sàn"])
    m5 -- "tên sản phẩm" --> ext
```

Trạng thái rỗng của SCR-05, SCR-06, SCR-07 và trang Tổng quan đều có nút **Bắt đầu tìm kiếm** dẫn về SCR-03.

## Nội dung từng màn hình (sitemap chi tiết)

Mỗi cột là một màn hình, các khối xếp theo thứ tự từ trên xuống như trên giao diện, kèm mô tả ngắn nội dung.

### Thành phần dùng chung

Có mặt trên mọi màn hình SCR-02 → SCR-07; SCR-01 chỉ có nút sáng / tối.

```mermaid
flowchart TB
    shell(["Khung ứng dụng — App.tsx"]) --> side & head
    subgraph side["Thanh bên — Sidebar.tsx"]
        direction TB
        s1["<b>Logo + tên hệ thống</b><br/>Shopping AI, nút thu gọn / mở rộng"]
        s2["<b>Chức năng chính</b><br/>6 mục menu, mục đang mở được tô đậm,<br/>thu gọn chỉ còn biểu tượng + tooltip"]
        s3["<b>Trợ giúp và hỗ trợ</b><br/>Gửi góp ý, Yêu cầu hỗ trợ, Cài đặt,<br/>Cài đặt nguồn dữ liệu (quản trị viên)"]
        s4["<b>Khẩu hiệu</b><br/>Đề xuất có trách nhiệm."]
        s1 ~~~ s2 ~~~ s3 ~~~ s4
    end
    subgraph head["Thanh tiêu đề — Header.tsx"]
        direction TB
        h1["<b>Tên màn hình hiện tại</b>"]
        h2["<b>Nguồn dữ liệu: N nền tảng</b><br/>chỉ quản trị viên, mở hộp thoại nguồn và kho dữ liệu"]
        h3["<b>Nút sáng / tối</b><br/>nhớ lựa chọn theo trình duyệt"]
        h4["<b>Menu tài khoản</b><br/>chữ viết tắt + tên, email, nhãn Quản trị viên,<br/>Tài khoản và mật khẩu, Đăng xuất"]
        h1 ~~~ h2 ~~~ h3 ~~~ h4
    end
```

### SCR-01 Đăng nhập / Đăng ký và SCR-02 Tổng quan

```mermaid
flowchart TB
    root(["Shopping AI"]) --> a & d
    subgraph a["SCR-01 Đăng nhập / Đăng ký — AuthView.tsx"]
        direction TB
        a1["<b>Nút sáng / tối</b><br/>góc trên phải"]
        a2["<b>Thương hiệu</b><br/>logo, Shopping AI, câu giới thiệu"]
        a3["<b>Thẻ chọn</b><br/>Đăng nhập | Đăng ký"]
        a4["<b>Biểu mẫu</b><br/>Đăng nhập: email, mật khẩu có nút hiện / ẩn<br/>Đăng ký: thêm tên hiển thị, nhập lại mật khẩu,<br/>gợi ý độ mạnh mật khẩu"]
        a5["<b>Thông báo lỗi</b><br/>lỗi từng ô và lỗi từ máy chủ"]
        a6["<b>Nút gửi</b><br/>Đăng nhập / Tạo tài khoản"]
        a7["<b>Chuyển chế độ</b><br/>Chưa có tài khoản? Đăng ký ngay"]
        a8["<b>Ghi chú</b><br/>dữ liệu lưu theo tài khoản, dùng trên mọi thiết bị"]
        a1 ~~~ a2 ~~~ a3 ~~~ a4 ~~~ a5 ~~~ a6 ~~~ a7 ~~~ a8
    end
    subgraph d["SCR-02 Tổng quan — DashboardView.tsx"]
        direction TB
        d1["<b>Lời chào</b><br/>Xin chào + mô tả trang"]
        d2["<b>Thao tác nhanh</b><br/>4 thẻ: Tư vấn mua sắm, Tra cứu bảo hành và đổi trả,<br/>Sản phẩm đã lưu, Lịch sử hoạt động"]
        d3["<b>Thống kê</b><br/>5 ô: lượt tìm kiếm, sản phẩm đã đề xuất,<br/>đã lưu, đang theo dõi giá, nền tảng nguồn"]
        d4["<b>Tìm kiếm gần đây</b><br/>câu hỏi + sản phẩm hạng 1, bấm để mở lại trong chat"]
        d5["<b>Đã lưu gần đây</b><br/>sản phẩm mới lưu, liên kết Xem tất cả"]
        d1 ~~~ d2 ~~~ d3 ~~~ d4 ~~~ d5
    end
```

### SCR-03 Tư vấn mua sắm

Màn hình chính có bốn chế độ xem con theo tiến trình một lượt tư vấn.

```mermaid
flowchart TB
    scr["SCR-03 Tư vấn mua sắm<br/>SearchAssistantView.tsx"]
    scr --> conv
    scr --> v1 & v2 & v3 & v4
    scr --> src

    subgraph conv["Danh sách hội thoại — ConversationList.tsx"]
        direction TB
        c1["<b>Tiêu đề</b><br/>HỘI THOẠI + nút tạo mới"]
        c2["<b>Danh sách</b><br/>tên = câu hỏi đầu tiên, tối đa 30,<br/>nút xóa có xác nhận"]
        c3["<b>Màn hình hẹp</b><br/>thay bằng menu chọn hội thoại"]
        c1 ~~~ c2 ~~~ c3
    end

    subgraph v1["A. Hội thoại trống"]
        direction TB
        e1["<b>Lời mời</b><br/>Mô tả nhu cầu mua sắm của bạn + giải thích quy trình"]
        e2["<b>Câu hỏi mẫu</b><br/>4 gợi ý bấm để gửi"]
        e3["<b>Liên kết phụ</b><br/>tra cứu chính sách bảo hành, đổi trả"]
        e4["<b>Ô nhập</b><br/>ô mô tả nhu cầu, nút Gửi,<br/>lưu ý AI có thể sai"]
        e1 ~~~ e2 ~~~ e3 ~~~ e4
    end

    subgraph v2["B. Đang xử lý"]
        direction TB
        p1["<b>Tin nhắn người dùng</b>"]
        p2["<b>Tiến trình của agent</b><br/>các bước: phân tích yêu cầu, thu thập dữ liệu,<br/>nới lỏng tiêu chí, soạn lời khuyên..."]
        p3["<b>Ô nhập bị khóa</b><br/>không chuyển / xóa hội thoại"]
        p1 ~~~ p2 ~~~ p3
    end

    subgraph v3["C. Câu hỏi làm rõ"]
        direction TB
        q1["<b>Thẻ làm rõ</b><br/>Làm rõ nhu cầu để xếp hạng chính xác hơn"]
        q2["<b>Lựa chọn</b><br/>các mức ngân sách theo ngành hàng"]
        q3["<b>Gợi ý trả lời tự do</b><br/>gõ vào ô chat"]
        q4["<b>Nút</b><br/>Bỏ qua, Xác nhận"]
        q1 ~~~ q2 ~~~ q3 ~~~ q4
    end

    subgraph v4["D. Kết quả tư vấn"]
        direction TB
        r1["<b>Lời tư vấn</b><br/>Trợ lý mua sắm, giờ, nội dung Markdown"]
        r2["<b>Lưu ý về dữ liệu</b><br/>độ mới, nới tiêu chí, nguồn chưa xác minh"]
        r3["<b>Sản phẩm đề xuất N</b><br/>thẻ: ảnh, tên, Phù hợp %, nơi bán, giá,<br/>giá gốc, đánh giá, nhãn cấu hình, ưu / nhược,<br/>bảo hành · đổi trả, Lưu, Theo dõi giá, Xem tại sàn"]
        r4["<b>Bảng so sánh</b><br/>Xem / Ẩn bảng so sánh chi tiết: phù hợp, giá,<br/>đánh giá, nơi bán, ưu, nhược, bảo hành, đổi trả"]
        r5["<b>Nguồn N</b><br/>trang sản phẩm đã thu thập, bấm để xem chi tiết"]
        r6["<b>Câu hỏi gợi ý</b><br/>chỉ ở câu trả lời mới nhất"]
        r7["<b>Nút tra cứu chính sách</b><br/>khi câu hỏi liên quan bảo hành, đổi trả"]
        r1 ~~~ r2 ~~~ r3 ~~~ r4 ~~~ r5 ~~~ r6 ~~~ r7
    end

    subgraph src["Bảng chi tiết nguồn"]
        direction TB
        n1["<b>Nguồn số i</b><br/>tên sàn, tiêu đề"]
        n2["<b>Giá ghi nhận</b>"]
        n3["<b>Nội dung thu thập được</b><br/>bảo hành, đổi trả, thông số chính"]
        n4["<b>Thời điểm thu thập</b>"]
        n5["<b>Mở trang gốc</b>"]
        n1 ~~~ n2 ~~~ n3 ~~~ n4 ~~~ n5
    end
```

### SCR-04 Tra cứu bảo hành và đổi trả, SCR-05 Sản phẩm đã lưu

```mermaid
flowchart TB
    shell(["Khung ứng dụng"]) --> p & s
    subgraph p["SCR-04 Tra cứu chính sách — PolicyLookupView.tsx"]
        direction TB
        p1["<b>Tiêu đề + mô tả</b>"]
        p2["<b>Ô tìm kiếm</b><br/>tên sản phẩm hoặc link, nút Tra cứu bằng AI"]
        p3["<b>Chọn nền tảng</b><br/>chỉ các nguồn đang bật trong DLG-02"]
        p4["<b>Bảng so sánh chính sách</b><br/>thời hạn đổi trả, trả hàng miễn phí, điều kiện,<br/>phí vận chuyển trả hàng, thời gian hoàn tiền,<br/>lỗi nhà sản xuất, tiếp nhận bảo hành, ngoại lệ, nguồn"]
        p5["<b>Lưu ý</b><br/>chính sách thay đổi theo ngành hàng, gian hàng"]
        p1 ~~~ p2 ~~~ p3 ~~~ p4 ~~~ p5
    end
    subgraph s["SCR-05 Sản phẩm đã lưu — SavedProductsView.tsx"]
        direction TB
        s1["<b>Tiêu đề + hướng dẫn</b><br/>chọn từ 2 sản phẩm để nhờ AI so sánh"]
        s2["<b>Nút Nhờ AI so sánh N</b><br/>mở SCR-03 với bảng so sánh"]
        s3["<b>Ô tìm</b><br/>theo tên, hãng, câu tìm kiếm"]
        s4["<b>Lưới thẻ sản phẩm</b><br/>ô chọn, ảnh, tên, giá, bảo hành, đổi trả,<br/>Từ tìm kiếm, Theo dõi giá, Bỏ lưu"]
        s5["<b>Trạng thái rỗng</b><br/>hướng dẫn + Bắt đầu tìm kiếm"]
        s1 ~~~ s2 ~~~ s3 ~~~ s4 ~~~ s5
    end
```

### SCR-06 Theo dõi giá, SCR-07 Lịch sử hoạt động

```mermaid
flowchart TB
    shell(["Khung ứng dụng"]) --> al & ac
    subgraph al["SCR-06 Theo dõi giá — PriceAlertsView.tsx"]
        direction TB
        a1["<b>Tiêu đề</b><br/>số yêu cầu, nút Kiểm tra tất cả ngay"]
        a2["<b>Thẻ theo dõi</b><br/>ảnh, tên có liên kết, nhãn trạng thái:<br/>Đang theo dõi / Đã đạt giá, Hết hàng, Chờ xác nhận giá"]
        a3["<b>Các mức giá</b><br/>giá mong muốn, giá gần nhất,<br/>thấp nhất đã thấy, lúc bắt đầu"]
        a4["<b>Khoảng cách</b><br/>còn cách mức mong muốn, lần kiểm tra cuối"]
        a5["<b>Thao tác</b><br/>Lịch sử giá, Nhật ký kiểm tra,<br/>Kiểm tra ngay, Bỏ theo dõi"]
        a6["<b>Mở rộng</b><br/>biểu đồ + bảng lịch sử giá,<br/>bảng nhật ký: thời điểm, kết quả, giá đọc được, ghi chú"]
        a7["<b>Trạng thái rỗng</b><br/>hướng dẫn + Bắt đầu tìm kiếm"]
        a1 ~~~ a2 ~~~ a3 ~~~ a4 ~~~ a5 ~~~ a6 ~~~ a7
    end
    subgraph ac["SCR-07 Lịch sử hoạt động — ActivityLogView.tsx"]
        direction TB
        h1["<b>Tiêu đề</b><br/>nút Xóa lịch sử có xác nhận"]
        h2["<b>Ô tìm</b><br/>tìm trong lịch sử"]
        h3["<b>Bộ lọc loại</b><br/>Tất cả, Tìm kiếm, Lưu sản phẩm, Bỏ lưu, So sánh,<br/>Tra cứu chính sách, Cài đặt, Theo dõi giá, Góp ý và hỗ trợ"]
        h4["<b>Nhóm theo ngày</b><br/>Hôm nay, Hôm qua, ngày cụ thể"]
        h5["<b>Dòng hoạt động</b><br/>tiêu đề, chi tiết, loại · giờ, Mở lại"]
        h6["<b>Trạng thái rỗng</b><br/>chưa có hoạt động / không khớp bộ lọc"]
        h1 ~~~ h2 ~~~ h3 ~~~ h4 ~~~ h5 ~~~ h6
    end
```

### Hộp thoại

```mermaid
flowchart TB
    shell(["Mở từ thẻ sản phẩm, thanh bên, thanh tiêu đề"]) --> t & g & f & k & pr
    subgraph t["DLG-01 Theo dõi giá"]
        direction TB
        t1["<b>Sản phẩm</b><br/>tên, giá hiện tại"]
        t2["<b>Lịch sử giá</b><br/>biểu đồ"]
        t3["<b>Báo cho tôi khi giá xuống</b><br/>mức gợi ý −5 … −20% hoặc nhập giá"]
        t4["<b>Kiểm tra hợp lệ</b><br/>phải thấp hơn giá hiện tại"]
        t5["<b>Nút</b><br/>Hủy, Theo dõi giá, Bỏ theo dõi nếu đang theo dõi"]
        t1 ~~~ t2 ~~~ t3 ~~~ t4 ~~~ t5
    end
    subgraph g["DLG-02 Nguồn và kho dữ liệu"]
        direction TB
        g1["<b>Nguồn được phép thu thập</b><br/>bật / tắt từng sàn"]
        g2["<b>Kho dữ liệu</b><br/>số sản phẩm, cập nhật gần nhất"]
        g3["<b>Thu thập lại ngay</b><br/>chỉ quản trị viên, người khác thấy ghi chú"]
        g1 ~~~ g2 ~~~ g3
    end
    subgraph f["DLG-03 Góp ý / Hỗ trợ"]
        direction TB
        f1["<b>Chủ đề</b><br/>góp ý: chất lượng tư vấn, kết quả, giao diện, tính năng<br/>hỗ trợ: lỗi tìm kiếm, kết nối, sai giá, khác"]
        f2["<b>Nội dung</b>"]
        f3["<b>Liên hệ</b><br/>không bắt buộc"]
        f4["<b>Gửi → Đã ghi nhận</b><br/>lưu vào Lịch sử hoạt động"]
        f1 ~~~ f2 ~~~ f3 ~~~ f4
    end
    subgraph k["DLG-04 Tài khoản"]
        direction TB
        k1["<b>Thông tin</b><br/>email, vai trò"]
        k2["<b>Tên hiển thị</b><br/>sửa và lưu"]
        k3["<b>Đổi mật khẩu</b><br/>hiện tại, mới, nhập lại"]
        k1 ~~~ k2 ~~~ k3
    end
    subgraph pr["DLG-05 Cài đặt"]
        direction TB
        r1["<b>Giao diện</b><br/>Sáng · Tối · Tự động theo giờ"]
        r2["<b>Khung giờ tối</b><br/>khi chọn tự động, mặc định 18:00–06:00"]
        r3["<b>Ngôn ngữ</b><br/>Tiếng Việt · English"]
        r4["<b>Ghi chú</b><br/>lưu theo tài khoản, áp dụng mọi thiết bị"]
        r1 ~~~ r2 ~~~ r3 ~~~ r4
    end
```

## Wireframe

Bố cục phác thảo của các màn hình chính (màn hình rộng).

**Khung ứng dụng + SCR-03 Tư vấn mua sắm (kết quả)**

```text
┌──────────────┬───────────────────────────────────────────────────────────────────┐
│ ◆ Shopping AI│ Tư vấn mua sắm        [Nguồn dữ liệu: 3 nền tảng] [☾] │ (NV) Tên ▾ │
│──────────────├──────────────┬────────────────────────────────────────────────────┤
│ ▣ Tổng quan  │ HỘI THOẠI  + │  Bạn: Laptop gaming dưới 25 triệu có RTX 4050      │
│ ▣ Tư vấn ◀   │──────────────│                                                    │
│ ▣ Tra cứu    │ ▸ Laptop ... │  Trợ lý mua sắm · 14:02                            │
│ ▣ Đã lưu     │   Máy giặt ..│  Lời tư vấn (Markdown) ...                         │
│ ▣ Theo dõi   │   Tai nghe ..│  ┌ ⚠ Lưu ý về dữ liệu ────────────────────────┐   │
│ ▣ Lịch sử    │              │  └────────────────────────────────────────────┘   │
│              │              │  Sản phẩm đề xuất (3)                              │
│ TRỢ GIÚP     │              │  ┌──────┬───────────────────────────────────────┐ │
│ ✎ Góp ý      │              │  │ ảnh  │ Tên sản phẩm      Phù hợp 86%          │ │
│ ⛑ Hỗ trợ     │              │  │      │ Nơi bán · sàn  24.990.000 ₫ ̶2̶7̶.̶9̶9̶0̶...│ │
│ ⚙ Nguồn      │              │  │      │ [Đúng cấu hình] + ưu | − nhược         │ │
│              │              │  │      │ [Lưu] [Theo dõi giá] Xem tại sàn ↗     │ │
│ Đề xuất có   │              │  └──────┴───────────────────────────────────────┘ │
│ trách nhiệm. │              │  [▾ Xem bảng so sánh chi tiết]   Nguồn (3): [1][2] │
│              │              │  (gợi ý) (gợi ý) (gợi ý)                           │
│              │              │ ┌────────────────────────────────────────┐ [Gửi]  │
│ [«]          │              │ │ VD: Laptop gaming dưới 30 triệu ...    │        │
│              │              │ └────────────────────────────────────────┘        │
└──────────────┴──────────────┴────────────────────────────────────────────────────┘
```

**SCR-02 Tổng quan**

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Xin chào                                                             │
│ Tổng quan hoạt động tìm kiếm, sản phẩm đã lưu và nguồn dữ liệu...    │
│ THAO TÁC NHANH                                                       │
│ [Tư vấn mua sắm] [Tra cứu bảo hành] [Sản phẩm đã lưu] [Lịch sử]      │
│ [Lượt tìm] [Đã đề xuất] [Đã lưu] [Theo dõi giá] [Nền tảng]  ← 5 số   │
│ ┌ Tìm kiếm gần đây ───────────┐  ┌ Đã lưu gần đây ── Xem tất cả ┐   │
│ │ câu hỏi → Hạng 1: ...       │  │ ảnh · tên · giá              │   │
│ └─────────────────────────────┘  └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**SCR-06 Theo dõi giá**

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Theo dõi giá                                  [↻ Kiểm tra tất cả ngay]│
│ ┌──────┬─────────────────────────────────────────── [Đang theo dõi] ┐│
│ │ ảnh  │ Tên sản phẩm ↗                                              ││
│ │      │ Mong muốn | Gần nhất | Thấp nhất đã thấy | Lúc bắt đầu      ││
│ │      │ Còn cách mức mong muốn ... · kiểm tra lúc 14:00             ││
│ │      │ [Lịch sử giá] [↻ Kiểm tra ngay]               [🗑 Bỏ theo dõi]││
│ └──────┴─────────────────────────────────────────────────────────────┘│
│   └─ mở rộng: biểu đồ giá + bảng Thời điểm | Giá bán                  │
└──────────────────────────────────────────────────────────────────────┘
```

**SCR-01 Đăng nhập / Đăng ký**

```text
┌──────────────────────────────────────────┐
│                                     [☾]  │
│               ◆ Shopping AI              │
│   Trợ lý mua sắm thông minh: ...         │
│   ┌──────────────────────────────────┐   │
│   │ [ Đăng nhập ][  Đăng ký  ]       │   │
│   │ Email          [____________]    │   │
│   │ Mật khẩu       [__________ 👁]   │   │
│   │ [          Đăng nhập          ]  │   │
│   │ Chưa có tài khoản? Đăng ký ngay  │   │
│   └──────────────────────────────────┘   │
│   Dữ liệu lưu theo tài khoản ...         │
└──────────────────────────────────────────┘
```

## Hệ thống nhãn

| Đối tượng | Nhãn trên thanh bên | Nhãn trên thanh tiêu đề / tiêu đề trang | Ghi chú |
|---|---|---|---|
| SCR-02 | Tổng quan | Tổng quan | Thống nhất |
| SCR-03 | Tư vấn mua sắm | Tư vấn mua sắm | Thống nhất |
| SCR-04 | Tra cứu bảo hành & đổi trả | Tra cứu bảo hành & đổi trả | Đã thống nhất (tiêu đề trong trang vẫn là "Tra cứu chính sách bảo hành & đổi trả") |
| SCR-05 | Sản phẩm đã lưu | Sản phẩm đã lưu | Thống nhất |
| SCR-06 | Theo dõi giá | Theo dõi giá | Thống nhất |
| SCR-07 | Lịch sử hoạt động | Lịch sử hoạt động | Thống nhất |
| DLG-02 | Cài đặt nguồn dữ liệu (quản trị viên) | Nguồn & kho dữ liệu (nút trên thanh tiêu đề: "Nguồn dữ liệu: N nền tảng") | ⚠ Ba cách gọi cho cùng một hộp thoại |
| DLG-05 | Cài đặt | Cài đặt | Thống nhất; tiếng Anh: "Settings" |

| Hành động / trạng thái | Nhãn đang dùng | Ghi chú |
|---|---|---|
| Lưu sản phẩm | Lưu sản phẩm ↔ Đã lưu; trong SCR-05: Bỏ lưu | Thống nhất |
| Theo dõi giá | Thẻ chat: Theo dõi giá ↔ Đang theo dõi giá; SCR-05: Theo dõi giá ↔ Đang theo dõi | ⚠ Lệch nhẹ giữa hai màn hình |
| Trạng thái theo dõi | Đang theo dõi, Đã đạt giá; nhãn phụ Hết hàng, Chờ xác nhận giá | |
| Mức khớp cấu hình | Đúng cấu hình yêu cầu, Không đúng cấu hình yêu cầu, Chưa xác minh cấu hình | |
| Mức phù hợp | Phù hợp N% | |
| Liên kết ra sàn | Xem tại sàn (thẻ sản phẩm), Mở trang gốc (bảng nguồn) | ⚠ Hai nhãn cho cùng hành động |
| Bắt đầu lại | Bắt đầu tìm kiếm (mọi trạng thái rỗng), Mở lại (lịch sử), Hội thoại mới | |

## Hợp đồng trạng thái giao diện

| Trạng thái | Cách hiển thị |
|---|---|
| Đang kiểm tra phiên | Vòng xoay "Đang kiểm tra phiên đăng nhập..." |
| Agent đang xử lý | Timeline "Tiến trình của agent" theo sự kiện `status`; ô nhập và việc chuyển hội thoại bị khóa |
| Không có kết quả | Lời tư vấn nói rõ không tìm thấy, không đưa giá; gợi ý nới tiêu chí |
| Dữ liệu chưa chắc chắn | Khung "Lưu ý về dữ liệu" (`search_notes`); nhãn "Chưa xác minh cấu hình" |
| Sai cấu hình yêu cầu | Nhãn đỏ "Không đúng cấu hình yêu cầu" + lý do |
| Lỗi backend | Tin nhắn lỗi có biểu tượng cảnh báo, ghi địa chỉ backend và lệnh khởi động |
| Danh sách rỗng | Thẻ hướng dẫn + nút "Bắt đầu tìm kiếm" |
| Ảnh sản phẩm lỗi / chưa tải | Ô xám biểu tượng ảnh, không để chữ alt tràn khung |

## Responsive và khả năng truy cập

- Màn hình hẹp: danh sách hội thoại chuyển thành menu chọn; thanh bên thu gọn còn biểu tượng (tooltip tên mục).
- Nút chỉ có biểu tượng đều có `aria-label` / `title`; menu tài khoản dùng `aria-haspopup`, đóng bằng Esc.
- Trạng thái (đạt giá, sai cấu hình) luôn có biểu tượng + chữ, không chỉ dựa vào màu.
- Biểu đồ lịch sử giá có chế độ xem bảng.
- Chế độ sáng / tối / tự động theo giờ dùng chung bảng màu (biến CSS Tailwind 4), lưu theo tài khoản; `index.html` áp giao diện trước khi React chạy để không nháy màu.
- Hai ngôn ngữ Tiếng Việt / English (`src/i18n/`); `<html lang>` đổi theo; định dạng số và ngày theo ngôn ngữ.

## Ánh xạ màn hình → API

| Màn hình | API |
|---|---|
| SCR-01 | `POST /api/auth/register`, `POST /api/auth/login` |
| Khung ứng dụng | `GET /api/auth/me`, `POST /api/auth/logout`, `GET/PUT /api/auth/me/data/{key}` |
| SCR-03 | `POST /api/chat/stream`, `POST /api/chat/compare`, `DELETE /api/chat/history/{id}` |
| SCR-05 | `POST /api/chat/compare` (qua SCR-03), `PUT /api/auth/me/data/saved-products` |
| SCR-06, DLG-01 | `GET/POST/DELETE /api/alerts`, `POST /api/alerts/check`, `GET /api/alerts/{id}/checks`, `GET /api/products/{id}/history` |
| DLG-02 | `GET /api/crawler/status`, `POST /api/crawler/trigger` |
| DLG-04 | `PATCH /api/auth/me`, `POST /api/auth/change-password` |
| DLG-05 | `GET/PUT /api/auth/me/data/preferences`; ngôn ngữ gửi kèm `POST /api/chat/stream` (`language`) |
| SCR-02, SCR-07, DLG-03 | Dữ liệu cá nhân qua `/api/auth/me/data/{activities,search-history}` |
| SCR-04 | Không gọi API (dữ liệu tham khảo) |
