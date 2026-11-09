"""Giá trị điền sẵn không đọc từ trang sản phẩm (bảo hành, vận chuyển, số đánh giá) mà phiên bản cũ từng gán.

Dữ liệu đã lưu trong cache / CSDL / kho RAG vẫn có thể chứa các giá trị này: coi như chưa có dữ liệu,
để trợ lý nói "Chưa rõ" thay vì khẳng định một điều không có thật.
"""

PLACEHOLDER_WARRANTIES = frozenset(
    {
        "chính hãng",
        "chính hãng 12 tháng",
        "chính hãng tiki",
        "bảo hành 12 tháng tại hệ thống",
        "theo chính sách gian hàng",
    }
)
PLACEHOLDER_DELIVERY = frozenset(
    {
        "freeship",
        "tikinow",
        "tikinow giao 2h",
        "giao nhanh",
        "giao nhanh 2h",
        "giao hàng tiêu chuẩn",
        "tiêu chuẩn",
        "sẵn hàng tại siêu thị",
        "giao hàng & lắp đặt",
        "giao nhanh tại fpt shop",
        "giao nhanh tại cellphones",
    }
)
PLACEHOLDER_REVIEWS = frozenset({"chính hãng", "100+ đánh giá", "0 đánh giá"})


def known(value: object, placeholders: frozenset[str]) -> str | None:
    """Giá trị thật đã làm gọn; None nếu rỗng hoặc chỉ là giá trị điền sẵn."""
    text = str(value or "").strip()
    return None if not text or text.lower() in placeholders else text
