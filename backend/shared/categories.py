"""Mã ngành hàng chuẩn của hệ thống và các hàm thuần về danh mục (không cần CSDL / LLM).

Quy đổi danh mục của từng sàn sang mã chuẩn (cần bảng đã học + LLM): services/catalog/category_resolver.py.
"""

CANONICAL = {"laptops", "phones", "audio", "home_appliances", "fashion", "monitors", "beauty", "wearables", "other"}
FALLBACK = "other"
LABELS = {
    "laptops": "laptop",
    "phones": "điện thoại / máy tính bảng",
    "audio": "thiết bị âm thanh",
    "home_appliances": "đồ gia dụng, điện máy",
    "fashion": "thời trang",
    "monitors": "màn hình máy tính",
    "beauty": "làm đẹp, sức khỏe",
    "wearables": "đồng hồ / thiết bị đeo thông minh",
    "other": "khác (phụ kiện, linh kiện...)",
}

_ALIASES = {
    "laptop": "laptops",
    "notebook": "laptops",
    "phone": "phones",
    "smartphone": "phones",
    "headphone": "audio",
    "home_appliance": "home_appliances",
    "appliances": "home_appliances",
    "monitor": "monitors",
    "wearable": "wearables",
}


def canonical_code(code: str | None) -> str | None:
    if not code:
        return None
    c = code.strip().lower()
    c = _ALIASES.get(c, c)
    return c if c in CANONICAL or c == "all" else None


def tiki_path_from_breadcrumbs(breadcrumbs) -> str:
    return "/".join(str(b["category_id"]) for b in (breadcrumbs or []) if b.get("category_id"))


def category_path(prefix: str, names) -> str:
    return prefix + ":" + "/".join(n.strip() for n in names if n and n.strip() and n.strip() != "Root")
