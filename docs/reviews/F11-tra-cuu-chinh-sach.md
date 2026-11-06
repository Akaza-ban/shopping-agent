# F11 Tra cứu chính sách bảo hành & đổi trả — đánh giá

> Rà soát ngày 30/10/2026 · Mức: 🔴 Ưu tiên — màn hình đang hiển thị dữ liệu mẫu như dữ liệu thật
> Mã chính: [`frontend/src/components/PolicyLookupView.tsx`](../../frontend/src/components/PolicyLookupView.tsx), `PLATFORM_POLICIES`, `runPolicyLookup` trong [`frontend/src/services/shoppingService.ts`](../../frontend/src/services/shoppingService.ts)

## Đã làm được

- Bảo hành / đổi trả **của từng sản phẩm** lấy thật từ trang chi tiết, hiện trên thẻ sản phẩm và bảng so sánh (F04).
- Màn hình so sánh chính sách giữa các sàn: 9 hàng (thời hạn đổi trả, trả hàng miễn phí, điều kiện, phí trả hàng, hoàn tiền, lỗi nhà sản xuất, tiếp nhận bảo hành, ngoại lệ, nguồn); chọn sàn theo nguồn đang bật.

## Vấn đề

| # | Vấn đề | Ở đâu | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | Chính sách các sàn là dữ liệu cố định trong frontend | `PLATFORM_POLICIES` (có ghi chú "vẫn là dữ liệu mẫu") | Chính sách thay đổi mà màn hình không biết → người dùng nhận thông tin sai về quyền đổi trả | Cao |
| 2 | Nút "Tra cứu bằng AI" và các bước tiến trình chỉ mô phỏng | `runPolicyLookup` | Gây hiểu nhầm là có AI tra cứu thật | Cao |
| 3 | Ô nhập tên sản phẩm / link không ảnh hưởng kết quả | `PolicyLookupView.tsx` | Kết quả như nhau với mọi sản phẩm, trong khi chính sách khác theo ngành hàng | Trung bình |
| 4 | Không có ngày cập nhật cho từng chính sách | — | Không biết thông tin cũ đến đâu | Trung bình |

## Đề xuất cải thiện

1. **Trước mắt (nhỏ, nên làm ngay):** ghi rõ "Dữ liệu tham khảo, cập nhật ngày …" trên màn hình; bỏ hiệu ứng tiến trình giả; đổi nút thành "Xem chính sách" thay vì "Tra cứu bằng AI".
2. **Đưa dữ liệu chính sách về backend:** bảng `platform_policies (platform, category, field, value, source_url, fetched_at)` + `GET /api/policies?platform=&category=`; dữ liệu nạp từ trang chính sách chính thức của từng sàn.
3. **RAG chính sách** (bước 8 đã hoãn trong kế hoạch RAG): cào trang chính sách định kỳ, chia đoạn, nhúng bge-m3 vào collection riêng; trả lời câu hỏi "mua laptop ở TGDĐ đổi trả trong bao lâu" kèm trích dẫn đoạn gốc và ngày thu thập.
4. Kết hợp chính sách theo **sản phẩm cụ thể** (đã có từ trang chi tiết) với chính sách chung của sàn khi người dùng nhập link.

## Liên quan

[UC14](../03-use-cases.md), [11-rag.md §4](../11-rag.md), [arc42 §11 TD-03](../architecture/arc42/11-risks-and-technical-debt.md)
