import re
from typing import Any

from integrations.platforms.common import canonical_spec_label
from services.catalog.reviews import is_sold_label, parse_volume, review_count  # noqa: F401 (parse_volume: dùng lại từ đây)

# fit: mức hợp nhu cầu chấm từ thông số trên trang (spec_fit.py); thành phần nào không có dữ liệu thì bỏ khỏi trung bình
BASE_WEIGHTS = {"attributes": 35, "fit": 30, "budget": 20, "quality": 25, "deal": 10, "preference": 10}
PRIORITY_WEIGHTS = {
    "cheapest": {"attributes": 30, "fit": 10, "budget": 35, "quality": 15, "deal": 15, "preference": 5},
    "best_rating": {"attributes": 30, "fit": 15, "budget": 15, "quality": 40, "deal": 5, "preference": 10},
    "brand_reputation": {"attributes": 30, "fit": 20, "budget": 15, "quality": 25, "deal": 5, "preference": 25},
    "best_performance": {"attributes": 45, "fit": 45, "budget": 15, "quality": 25, "deal": 5, "preference": 10},
}
PRIOR_RATING = 4.0  # rating trung bình giả định khi ít dữ liệu
PRIOR_WEIGHT = 30  # số "lượt ảo" kéo về PRIOR_RATING
FIT_GOOD, FIT_POOR = 0.7, 0.4  # ngưỡng nêu lý do "hợp" / "không hợp" nhu cầu


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", "", str(s).lower())


def _spec_text(p: dict[str, Any]) -> str:
    specs = p.get("specs")
    if isinstance(specs, dict):
        return " ".join(f"{k} {v}" for k, v in specs.items())
    return str(specs or "")


def verifiable_attributes(criteria: Any) -> dict[str, str]:
    """Thông số yêu cầu có thể đối chiếu với tên / thông số sản phẩm (giá trị ngắn, VD "RTX 4070", "16GB")."""
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


def check_attribute(p: dict[str, Any], key: str, wanted: str) -> tuple[str, str | None]:
    """(verified | mismatch | unknown, giá trị thực tế khi mismatch) của một thông số yêu cầu trên sản phẩm.

    Sai cấu hình chỉ kết luận khi đã đọc trang chi tiết: dòng thông số cùng tên (GPU, CPU, RAM...) ghi giá trị khác,
    hoặc bước chấm theo thông số (spec_fit.py) chỉ ra giá trị thực tế chép nguyên văn từ bảng thông số.
    """
    haystack = _norm(f"{p.get('name', '')} {_spec_text(p)} {p.get('aiSummary', '')}")
    if _norm(wanted) in haystack:
        return "verified", None
    if not p.get("detailFetched"):
        return "unknown", None
    specs = p.get("specs") if isinstance(p.get("specs"), dict) else {}
    actual = specs.get(canonical_spec_label(key.upper() if len(key) <= 4 else key)) or specs.get(key)
    actual = actual or (p.get("specMismatch") or {}).get(key)
    return ("mismatch", str(actual)) if actual else ("unknown", None)


def score_product(p: dict[str, Any], criteria: Any) -> tuple[int, list[str], dict[str, str]]:
    """(điểm 0-100, lý do, trạng thái từng thông số yêu cầu) = trung bình có trọng số của 5 thành phần."""
    weights = PRIORITY_WEIGHTS.get(getattr(criteria, "priority", None) or "best_value", BASE_WEIGHTS)
    attributes, attr_reasons, attr_status = _score_attributes(p, criteria)
    fit, fit_reasons = _score_fit(p)
    budget, budget_reasons = _score_budget(p, criteria)
    quality, quality_reasons = _score_quality(p)
    deal, deal_reasons = _score_deal(p)
    preference = _score_preference(p, criteria)
    reasons = (
        attr_reasons
        + fit_reasons
        + budget_reasons
        + quality_reasons
        + deal_reasons
        + (["Đúng hãng bạn chọn"] if preference[1] else [])
    )

    parts = {
        "attributes": attributes,
        "fit": fit,
        "budget": budget,
        "quality": quality,
        "deal": deal,
        "preference": preference[0],
    }
    active = {k: w for k, w in weights.items() if parts.get(k) is not None}
    score = sum(parts[k] * w for k, w in active.items()) / (sum(active.values()) or 1) * 100
    if "mismatch" in attr_status.values():
        score = min(score, 55)
    return int(round(score)), reasons, attr_status


def _score_attributes(p: dict[str, Any], criteria: Any) -> tuple[float | None, list[str], dict[str, str]]:
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


def _score_fit(p: dict[str, Any]) -> tuple[float | None, list[str]]:
    """Mức hợp nhu cầu do spec_fit.py chấm từ thông số; None = chưa chấm được (không có thông số / LLM lỗi)."""
    fit = p.get("specFit")
    if not isinstance(fit, dict) or not isinstance(fit.get("score"), (int, float)):
        return None, []
    score, reason = float(fit["score"]), str(fit.get("reason") or "").strip()
    if not reason:
        return score, []
    if score >= FIT_GOOD:
        return score, [f"Hợp nhu cầu theo thông số: {reason}"]
    if score <= FIT_POOR:
        return score, [f"Không hợp nhu cầu theo thông số: {reason}"]
    return score, []


def _score_budget(p: dict[str, Any], criteria: Any) -> tuple[float, list[str]]:
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


def _score_quality(p: dict[str, Any]) -> tuple[float, list[str]]:
    """
    Trung bình Bayes theo số lượt đánh giá: ít lượt thì kéo về PRIOR_RATING.
    Sàn chỉ ghi số đã bán thì không biết điểm dựa trên bao nhiêu đánh giá: lượt bán chỉ chứng tỏ có người mua,
    nên tính tối đa bằng PRIOR_WEIGHT lượt (điểm và mức giả định nặng ngang nhau).
    """
    rating = float(p.get("rating") or 0)
    if rating <= 0:
        return 0.35, ["Chưa có đánh giá"]
    label = p.get("reviewsCount")
    volume = min(parse_volume(label), PRIOR_WEIGHT) if is_sold_label(label) else review_count(label)
    bayes = (volume * rating + PRIOR_WEIGHT * PRIOR_RATING) / (volume + PRIOR_WEIGHT)
    reasons = (
        [f"Đánh giá {rating:.1f}/5 từ {volume:,} lượt"]
        if not is_sold_label(label) and volume >= 100 and rating >= 4.5
        else []
    )
    return max(0.0, min(1.0, (bayes - 3.0) / 2.0)), reasons


def _score_deal(p: dict[str, Any]) -> tuple[float, list[str]]:
    """Giảm 30% trở lên là đủ điểm."""
    discount = int(p.get("discountPercent") or 0)
    return min(1.0, discount / 30), ([f"Đang giảm {discount}%"] if discount >= 10 else [])


def _score_preference(p: dict[str, Any], criteria: Any) -> tuple[float | None, bool]:
    """(điểm, có đúng hãng người dùng chọn): đúng hãng chọn = 1, hãng gợi ý = 0,5; None khi không nói tới hãng.

    Mức hợp nhu cầu không chấm ở đây (dò từ khóa trong tên) mà ở _score_fit, từ thông số trên trang.
    """
    brands = [b.lower() for b in (getattr(criteria, "brands", None) or [])]
    suggested = [b.lower() for b in (getattr(criteria, "suggested_brands", None) or [])]
    if not brands and not suggested:
        return None, False
    name_l = str(p.get("name", "")).lower()
    if brands and any(b in name_l for b in brands):
        return 1.0, True
    return (0.5 if any(b in name_l for b in suggested) else 0.0), False


def rank_products(products: list[dict[str, Any]], criteria: Any) -> tuple[list[dict[str, Any]], list[str]]:
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

    notes: list[str] = []
    wanted = _wanted_attributes(criteria)
    if wanted:
        mismatched = [p for p in scored if "mismatch" in p["attributeMatch"].values()]
        if mismatched:
            notes.append(
                f"{len(mismatched)} sản phẩm đã kiểm tra trang chi tiết và KHÔNG đúng yêu cầu "
                f"({', '.join(wanted.values())}); chỉ dùng làm phương án tham khảo."
            )
    return scored, notes
