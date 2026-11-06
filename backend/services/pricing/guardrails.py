
import logging
import re
from dataclasses import dataclass
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Tuple

from services.catalog.categories import categorize
from services.pricing.category_floors import category_floors

logger = logging.getLogger("price_guardrails")

MIN_PRICE = 10_000.0
MAX_PRICE = 500_000_000.0
MAX_DROP_PCT = 75.0
MAX_RISE_PCT = 200.0     
CONFIRM_DROP_PCT = 30.0
SAME_PRICE_TOLERANCE = 0.02


@dataclass(frozen=True)
class PriceVerdict:
    ok: bool
    rule: str = ""
    reason: str = ""


OK = PriceVerdict(True)


def _vnd(x: float) -> str:
    return f"{x:,.0f} đ".replace(",", ".")


def check_price(price: Optional[float], category: Optional[str] = None) -> PriceVerdict:
    """Giá tuyệt đối có hợp lý không (không cần lịch sử)."""
    if not price or price <= 0:
        return PriceVerdict(False, "missing", "Không có giá.")
    if price < MIN_PRICE:
        return PriceVerdict(False, "below_floor", f"Giá {_vnd(price)} thấp hơn mức tối thiểu {_vnd(MIN_PRICE)}.")
    if price > MAX_PRICE:
        return PriceVerdict(False, "above_ceiling", f"Giá {_vnd(price)} vượt mức tối đa {_vnd(MAX_PRICE)}.")
    floor = category_floors.get(category)
    if floor and price < floor:
        return PriceVerdict(False, "below_category_floor",
                            f"Giá {_vnd(price)} quá thấp cho danh mục {category} (tối thiểu {_vnd(floor)}).")
    return OK


def change_pct(price: float, reference: float) -> float:
    return (price - reference) / reference * 100.0


def check_change(price: float, reference: Optional[float]) -> PriceVerdict:
    """Biến động so với mốc giá trước có bất thường không."""
    if not reference or reference <= 0:
        return OK
    pct = change_pct(price, reference)
    if pct < -MAX_DROP_PCT:
        return PriceVerdict(False, "sudden_drop", f"Giá giảm {abs(pct):.0f}% so với {_vnd(reference)}.")
    if pct > MAX_RISE_PCT:
        return PriceVerdict(False, "sudden_rise", f"Giá tăng {pct:.0f}% so với {_vnd(reference)}.")
    return OK


def check_stock(in_stock: Optional[bool]) -> PriceVerdict:
    """Sàn báo hết hàng / ngừng kinh doanh. None (sàn không ghi) coi như còn hàng."""
    if in_stock is False:
        return PriceVerdict(False, "out_of_stock", "Sản phẩm đang hết hàng trên sàn.")
    return OK


def is_big_drop(price: float, reference: Optional[float]) -> bool:
    return bool(reference) and change_pct(price, reference) < -CONFIRM_DROP_PCT


def same_price(a: Optional[float], b: Optional[float]) -> bool:
    return bool(a) and bool(b) and abs(a - b) <= SAME_PRICE_TOLERANCE * max(a, b)


def product_key(name: str) -> str:
    """Khóa so khớp cùng sản phẩm giữa các bản ghi (tên viết thường, gộp khoảng trắng)."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def check_against_references(price: float, references: Iterable[float]) -> PriceVerdict:
    """Giá thấp bất thường so với trung vị giá của các bản ghi khác cùng sản phẩm."""
    refs = [r for r in references if r and r > 0]
    if not refs:
        return OK
    ref = median(refs)
    if change_pct(price, ref) < -MAX_DROP_PCT:
        return PriceVerdict(False, "outlier_low",
                            f"Giá {_vnd(price)} thấp bất thường so với {_vnd(ref)} của cùng sản phẩm.")
    return OK


def screen_products(
    products: List[Dict[str, Any]],
    reference_prices: Optional[Dict[str, List[float]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Tuple[Dict[str, Any], PriceVerdict]]]:
    
    reference_prices = reference_prices or {}
    batch: Dict[str, List[float]] = {}
    for p in products:
        batch.setdefault(product_key(p.get("name", "")), []).append(float(p.get("currentPrice") or 0))

    kept, rejected = [], []
    for p in products:
        price = float(p.get("currentPrice") or 0)
        verdict = check_price(price, categorize(p))
        if verdict.ok:
            key = product_key(p.get("name", ""))
            others = list(reference_prices.get(key, []))
            same_batch = batch.get(key, [])
            others += [x for i, x in enumerate(same_batch) if i != same_batch.index(price)]
            verdict = check_against_references(price, others)
        if verdict.ok:
            kept.append(p)
        else:
            rejected.append((p, verdict))
            logger.warning(f"[Price Guardrail] Loại '{p.get('name', '')[:60]}': {verdict.reason}")
    return kept, rejected
