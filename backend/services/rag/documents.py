import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.catalog.categories import categorize

Product = Dict[str, Any]

_GENERIC_WARRANTY = "Theo chính sách gian hàng"
_MAX_SPECS_CHARS = 1500


def _specs_text(specs: Any) -> str:
    if isinstance(specs, dict):
        return " - ".join(f"{k}: {v}" for k, v in specs.items() if k and v)
    if isinstance(specs, list):
        return " - ".join(str(item) for item in specs if item)
    return str(specs or "")


def build_document(p: Product) -> str:
    parts = [f"Tên sản phẩm: {p.get('name', '')}"]
    if p.get("categoryName"):
        parts.append(f"Ngành hàng: {p['categoryName']}")
    specs = _specs_text(p.get("specs"))
    if specs:
        parts.append(f"Thông số kỹ thuật: {specs[:_MAX_SPECS_CHARS]}")
    if p.get("warranty") and p["warranty"] != _GENERIC_WARRANTY:
        parts.append(f"Bảo hành: {p['warranty']}")
    return "\n".join(parts)


def build_metadata(pid: str, p: Product, updated_at: Optional[int] = None) -> Dict[str, Any]:
    """Metadata để lọc (chỉ kiểu nguyên thủy) + raw_json để dựng lại sản phẩm khi truy xuất."""
    p = {**p, "category": categorize(p)}
    price = float(p.get("currentPrice") or 0)
    return {
        "product_id": pid,
        "name": str(p.get("name", ""))[:200],
        "category": p["category"],
        "category_name": str(p.get("categoryName", "")),
        "platform": str(p.get("platform", "all")).lower(),
        "platform_name": str(p.get("platformName", "")),
        "current_price": price,
        "original_price": float(p.get("originalPrice") or price),
        "discount_percent": int(p.get("discountPercent") or 0),
        "rating": float(p.get("rating") or 0),
        "image": str(p.get("image", "")),
        "external_url": str(p.get("externalUrl", "")),
        "updated_at": int(updated_at or time.time()),
        "raw_json": json.dumps(p, ensure_ascii=False),
    }


def product_id(p: Product, taken: set) -> str:
    pid = str(p.get("id", "")).strip()
    if not pid or pid.endswith("-"):
        pid = f"{p.get('platform', 'item')}-{abs(hash(p.get('name', '') + p.get('externalUrl', ''))) % 1000000}"
    base, n = pid, 1
    while pid in taken:
        pid, n = f"{base}-{n}", n + 1
    return pid


def product_from_metadata(meta: Dict[str, Any]) -> Product:
    try:
        product = json.loads(meta["raw_json"])
    except (KeyError, TypeError, ValueError):
        product = dict(meta)
    product["category"] = meta.get("category", product.get("category"))
    if not product.get("updatedAt") and meta.get("updated_at"):
        product["updatedAt"] = datetime.fromtimestamp(meta["updated_at"], tz=timezone.utc).isoformat()
    return product
