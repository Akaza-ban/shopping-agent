import re
from typing import Any, Dict, List, Optional, Tuple

from services.catalog.platforms.common import canonical_spec_label

BASE_WEIGHTS = {"attributes": 35, "budget": 20, "quality": 25, "deal": 10, "preference": 10}
PRIORITY_WEIGHTS = {
    "cheapest": {"attributes": 30, "budget": 35, "quality": 15, "deal": 15, "preference": 5},
    "best_rating": {"attributes": 30, "budget": 15, "quality": 40, "deal": 5, "preference": 10},
    "brand_reputation": {"attributes": 30, "budget": 15, "quality": 25, "deal": 5, "preference": 25},
    "best_performance": {"attributes": 45, "budget": 15, "quality": 25, "deal": 5, "preference": 10},
}
PRIOR_RATING = 4.0       # rating trung bình giả định khi ít dữ liệu
PRIOR_WEIGHT = 30        # số "lượt ảo" kéo về PRIOR_RATING
ATTRIBUTE_KEY_ALIASES = {"ssd": "Lưu trữ", "storage": "Lưu trữ", "rom": "Lưu trữ", "screen": "Kích thước màn hình",
                         "battery": "Pin", "weight": "Khối lượng", "os": "Hệ điều hành"}
USAGE_KEYWORDS = {"chơi game": ["gaming", "game"], "gaming": ["gaming", "game"], "đồ họa": ["creator", "studio", "oled"]}
GENERIC_WORDS = {"laptop", "điện", "thoại", "máy", "tính", "tai", "nghe", "chính", "hãng", "mới", "giá", "rẻ"}


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", "", str(s).lower())


def parse_volume(text: Any) -> int:
    """'Đã bán 3,4k' -> 3400, '12 đánh giá' -> 12, 'Chưa có đánh giá' -> 0."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|nghìn)?", str(text or "").lower())
    if not m:
        return 0
    value = float(m.group(1).replace(",", "."))
    return int(value * 1000) if m.group(2) else int(value)


def _spec_text(p: Dict[str, Any]) -> str:
    specs = p.get("specs")
    if isinstance(specs, dict):
        return " ".join(f"{k} {v}" for k, v in specs.items())
    return str(specs or "")


def verifiable_attributes(criteria: Any) -> Dict[str, str]:
   
    attrs = getattr(criteria, "attributes", None) or {}
    result = {}
    for k, v in attrs.items():
        if isinstance(v, bool) or not isinstance(v, (str, int, float)):
            continue
        text = str(v).strip()
        if text and len(text.split()) <= 3 and len(text) <= 25:
            result[str(k)] = text
    return result


_wanted_attributes = verifiable_attributes


def check_attribute(p: Dict[str, Any], key: str, wanted: str) -> Tuple[str, Optional[str]]:
   
    haystack = _norm(f"{p.get('name', '')} {_spec_text(p)} {p.get('aiSummary', '')}")
    if _norm(wanted) in haystack:
        return "verified", None
    specs = p.get("specs") if isinstance(p.get("specs"), dict) else {}
    canonical = ATTRIBUTE_KEY_ALIASES.get(key.lower(), canonical_spec_label(key.upper() if len(key) <= 4 else key))
    actual = specs.get(canonical) or specs.get(key) or specs.get(key.upper())
    if actual and p.get("detailFetched"):
        return "mismatch", str(actual)
    return "unknown", None


def score_product(p: Dict[str, Any], criteria: Any) -> Tuple[int, List[str], Dict[str, str]]:
    """(điểm 0-100, lý do, trạng thái từng thông số yêu cầu) = trung bình có trọng số của 5 thành phần."""
    weights = PRIORITY_WEIGHTS.get(getattr(criteria, "priority", None) or "best_value", BASE_WEIGHTS)
    attributes, attr_reasons, attr_status = _score_attributes(p, criteria)
    budget, budget_reasons = _score_budget(p, criteria)
    quality, quality_reasons = _score_quality(p)
    deal, deal_reasons = _score_deal(p)
    preference = _score_preference(p, criteria)
    reasons = attr_reasons + budget_reasons + quality_reasons + deal_reasons + (["Đúng hãng bạn chọn"] if preference[1] else [])

    parts = {"attributes": attributes, "budget": budget, "quality": quality, "deal": deal, "preference": preference[0]}
    active = {k: w for k, w in weights.items() if parts.get(k) is not None}
    score = sum(parts[k] * w for k, w in active.items()) / (sum(active.values()) or 1) * 100
    if "mismatch" in attr_status.values():
        score = min(score, 55)
    return int(round(score)), reasons, attr_status


def _score_attributes(p: Dict[str, Any], criteria: Any) -> Tuple[Optional[float], List[str], Dict[str, str]]:
    """Tỉ lệ thông số yêu cầu đúng; chưa xác minh được tính 0,3 (thấp nhưng không bằng sai hẳn). None = không yêu cầu."""
    wanted = _wanted_attributes(criteria)
    if not wanted:
        return None, [], {}
    got, reasons, status_by_key = 0.0, [], {}
    for key, value in wanted.items():
        status, actual = check_attribute(p, key, value)
        status_by_key[key] = status
        if status == "verified":
            got += 1
            reasons.append(f"Đúng yêu cầu {value}")
        elif status == "mismatch":
            reasons.append(f"Không đúng yêu cầu {value} (thực tế: {actual[:60]})")
        else:
            got += 0.3
            reasons.append(f"Chưa xác minh được {value}")
    return got / len(wanted), reasons, status_by_key


def _score_budget(p: Dict[str, Any], criteria: Any) -> Tuple[float, List[str]]:
    """Trong ngân sách = 1; vượt thì giảm nhanh (vượt 20% -> 0); không nêu ngân sách = 0,5."""
    price = float(p.get("currentPrice") or 0)
    max_p, min_p = getattr(criteria, "max_price", None), getattr(criteria, "min_price", None)
    if max_p:
        if price <= max_p:
            return 1.0, [f"Trong ngân sách (còn dư {max_p - price:,.0f} đ)"]
        return max(0.0, 1 - (price - max_p) / max_p * 5), [f"Vượt ngân sách {price - max_p:,.0f} đ"]
    if min_p:
        return (1.0 if price >= min_p else 0.5), []
    return 0.5, []


def _score_quality(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Trung bình Bayes theo số lượt đánh giá / đã bán: ít lượt thì kéo về PRIOR_RATING."""
    rating = float(p.get("rating") or 0)
    if rating <= 0:
        return 0.35, ["Chưa có đánh giá"]
    volume = parse_volume(p.get("reviewsCount"))
    bayes = (volume * rating + PRIOR_WEIGHT * PRIOR_RATING) / (volume + PRIOR_WEIGHT)
    reasons = [f"Đánh giá {rating:.1f}/5 từ {volume:,} lượt"] if volume >= 100 and rating >= 4.5 else []
    return max(0.0, min(1.0, (bayes - 3.0) / 2.0)), reasons


def _score_deal(p: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Giảm 30% trở lên là đủ điểm."""
    discount = int(p.get("discountPercent") or 0)
    return min(1.0, discount / 30), ([f"Đang giảm {discount}%"] if discount >= 10 else [])


def _score_preference(p: Dict[str, Any], criteria: Any) -> Tuple[float, bool]:
    """(điểm, có đúng hãng người dùng chọn): hãng chọn / hãng gợi ý, và tên khớp nhu cầu hoặc loại sản phẩm."""
    name_l = str(p.get("name", "")).lower()
    brands = [b.lower() for b in (getattr(criteria, "brands", None) or [])]
    suggested = [b.lower() for b in (getattr(criteria, "suggested_brands", None) or [])]
    chosen_brand = bool(brands) and any(b in name_l for b in brands)
    pref = 0.6 if chosen_brand else (0.3 if suggested and any(b in name_l for b in suggested) else 0.0)

    usage = (getattr(criteria, "usage_purpose", None) or "").lower()
    product_type = (getattr(criteria, "product_type", None) or "").lower()
    keywords = list(USAGE_KEYWORDS.get(usage, [])) + [
        w for w in re.findall(r"\w+", product_type) if len(w) > 2 and w not in GENERIC_WORDS]
    if keywords and any(k in name_l for k in keywords):
        pref += 0.4
    return min(1.0, pref), chosen_brand


def rank_products(products: List[Dict[str, Any]], criteria: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Chấm điểm, sắp xếp giảm dần; trả về (danh sách, ghi chú tổng hợp cho Advisor)."""
    if not products:
        return products, []
    scored = []
    for p in products:
        score, reasons, attr_status = score_product(p, criteria)
        item = dict(p)
        item["aiMatchScore"] = score
        item["matchReasons"] = reasons
        item["attributeMatch"] = attr_status
        scored.append(item)
    scored.sort(key=lambda x: (x["aiMatchScore"], -float(x.get("currentPrice") or 0)), reverse=True)

    notes: List[str] = []
    wanted = _wanted_attributes(criteria)
    if wanted:
        mismatched = [p for p in scored if "mismatch" in p["attributeMatch"].values()]
        if mismatched:
            notes.append(
                f"{len(mismatched)} sản phẩm đã kiểm tra trang chi tiết và KHÔNG đúng yêu cầu "
                f"({', '.join(wanted.values())}); chỉ dùng làm phương án tham khảo."
            )
    return scored, notes
