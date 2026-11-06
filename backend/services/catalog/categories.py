from typing import Any, Mapping, Optional

from services.catalog.category_codes import CANONICAL, FALLBACK, LABELS  
from services.catalog.category_resolver import category_resolver

_ALIASES = {
    "laptop": "laptops", "notebook": "laptops", "phone": "phones", "smartphone": "phones",
    "headphone": "audio", "home_appliance": "home_appliances", "appliances": "home_appliances",
    "monitor": "monitors", "wearable": "wearables",
}

def canonical_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = code.strip().lower()
    c = _ALIASES.get(c, c)
    return c if c in CANONICAL or c == "all" else None

def tiki_path_from_breadcrumbs(breadcrumbs) -> str:
    return "/".join(str(b["category_id"]) for b in (breadcrumbs or []) if b.get("category_id"))

def category_path(prefix: str, names) -> str:
    return prefix + ":" + "/".join(n.strip() for n in names if n and n.strip() and n.strip() != "Root")

def known_category(product: Mapping[str, Any]) -> Optional[str]:
    mapping = category_resolver.lookup(product)
    return mapping.category if mapping else None

def is_accessory(product: Mapping[str, Any]) -> Optional[bool]:
    mapping = category_resolver.lookup(product)
    return mapping.is_accessory if mapping else None

def categorize(product: Mapping[str, Any]) -> str:
    return known_category(product) or FALLBACK
