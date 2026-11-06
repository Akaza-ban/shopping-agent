"""Chính sách đổi trả, bảo hành nạp sẵn cho các nền tảng (tổng hợp thủ công từ trang chính sách, cần đối chiếu định kỳ)."""
from datetime import datetime

LAST_CHECKED = datetime(2026, 10, 26)

_RETAIL_TERMS = {
    "return_window_days": 30,
    "free_return": False,
    "return_shipping_fee": "Đổi trả trực tiếp tại cửa hàng",
    "defect_exchange": "1 đổi 1 trong 30 ngày nếu lỗi nhà sản xuất",
    "warranty_handling": "Cửa hàng tiếp nhận bảo hành hộ khách",
}

POLICY_SEED = [
    {
        "id": "tiki", "name": "Tiki Trading", "type": "Sàn TMĐT", "url": "https://hotro.tiki.vn",
        "terms": {
            "return_window_days": 30,
            "free_return": True,
            "return_conditions": ["Lỗi kỹ thuật, giao sai hoặc thiếu hàng", "Còn đầy đủ hộp, phụ kiện, hóa đơn"],
            "return_shipping_fee": "Miễn phí nếu lỗi do nhà bán hoặc nhà sản xuất",
            "refund_time": "3 - 5 ngày làm việc",
            "defect_exchange": "Đổi mới hoặc hoàn tiền trong thời hạn đổi trả",
            "warranty_handling": "Hãng hoặc Tiki tiếp nhận hộ (tùy ngành hàng)",
            "exceptions": ['Đổi trả vì lý do "không ưng" có thể không áp dụng với hàng điện tử'],
        },
    },
    {
        "id": "tgdd", "name": "Thế Giới Di Động", "type": "Chuỗi bán lẻ", "url": "https://www.thegioididong.com",
        "terms": {**_RETAIL_TERMS,
                  "return_conditions": ["1 đổi 1 nếu lỗi do nhà sản xuất", "Còn hộp, phụ kiện, không trầy xước, móp méo"],
                  "refund_time": "Hoàn tiền ngay tại cửa hàng",
                  "exceptions": ["Trả hàng không do lỗi sẽ bị trừ phí theo % giá trị sản phẩm"]},
    },
    {
        "id": "dmx", "name": "Điện Máy Xanh", "type": "Chuỗi bán lẻ", "url": "https://www.dienmayxanh.com",
        "terms": {**_RETAIL_TERMS,
                  "return_conditions": ["1 đổi 1 nếu lỗi do nhà sản xuất", "Còn hộp, phụ kiện, không trầy xước, móp méo"],
                  "refund_time": "Hoàn tiền ngay tại cửa hàng",
                  "exceptions": ["Trả hàng không do lỗi sẽ bị trừ phí theo % giá trị sản phẩm"]},
    },
    {
        "id": "fpt-shop", "name": "FPT Shop", "type": "Chuỗi bán lẻ", "url": "https://fptshop.com.vn",
        "terms": {**_RETAIL_TERMS,
                  "return_conditions": ["1 đổi 1 nếu lỗi do nhà sản xuất", "Còn hộp, phụ kiện, hóa đơn mua hàng"],
                  "refund_time": "Hoàn tiền tại cửa hàng hoặc chuyển khoản",
                  "exceptions": ["Trả hàng không do lỗi sẽ bị trừ phí theo % giá trị sản phẩm"]},
    },
    {
        "id": "cellphones", "name": "CellphoneS", "type": "Chuỗi bán lẻ", "url": "https://cellphones.com.vn",
        "terms": {**_RETAIL_TERMS,
                  "return_conditions": ["1 đổi 1 nếu lỗi do nhà sản xuất", "Còn hộp, phụ kiện, không có tác động vật lý"],
                  "refund_time": "Hoàn tiền tại cửa hàng",
                  "exceptions": ["Sản phẩm rơi vỡ, vào nước không được đổi trả"]},
    },
]


def document_text(name: str, terms: dict) -> str:
    """Nội dung trang chính sách dạng đoạn văn, mỗi đoạn là một ý để tách thành chunk."""
    paragraphs = [
        f"{name} cho đổi trả trong {terms['return_window_days']} ngày kể từ khi nhận hàng.",
        f"Điều kiện đổi trả tại {name}: " + "; ".join(terms["return_conditions"]) + ".",
        f"Phí vận chuyển khi trả hàng: {terms['return_shipping_fee']}.",
        f"Thời gian hoàn tiền: {terms['refund_time']}.",
        f"Sản phẩm lỗi nhà sản xuất: {terms['defect_exchange']}.",
        f"Bảo hành: {terms['warranty_handling']}.",
    ]
    paragraphs += [f"Lưu ý: {e}." for e in terms["exceptions"]]
    return "\n\n".join(paragraphs)
