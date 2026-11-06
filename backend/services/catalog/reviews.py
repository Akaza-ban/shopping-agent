"""Số lượt đánh giá thật và số lượt bán: hai con số khác nhau, nhiều sàn chỉ ghi số đã bán ở trang tìm kiếm."""
import re
from typing import Any

# Nhãn do adapter tạo khi sàn chỉ có số lượt bán (VD TGDĐ, FPT Shop): "Đã bán 3,4k"
SOLD_PREFIX = "Đã bán"


def sold_label(sold: Any) -> str:
    return f"{SOLD_PREFIX} {sold}" if sold else ""


def is_sold_label(text: Any) -> bool:
    return str(text or "").strip().lower().startswith(SOLD_PREFIX.lower())


def parse_volume(text: Any) -> int:
    """'Đã bán 3,4k' -> 3400, '12 đánh giá' -> 12, 'Chưa có đánh giá' -> 0."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|nghìn)?", str(text or "").lower())
    if not m:
        return 0
    value = float(m.group(1).replace(",", "."))
    return int(value * 1000) if m.group(2) else int(value)


def review_count(text: Any) -> int:
    """Số lượt đánh giá thật; 0 nếu sàn chỉ ghi số đã bán hoặc chưa có đánh giá."""
    return 0 if is_sold_label(text) else parse_volume(text)


def rating_text(rating: Any, reviews: Any) -> str:
    """Điểm đánh giá kèm đúng loại con số: "4.8/5 (120 đánh giá)" hoặc "5/5 (sàn không ghi số lượt đánh giá; Đã bán 1763)"."""
    label = str(reviews or "").strip()
    score = float(rating or 0)
    if score <= 0:
        return f"Chưa có điểm đánh giá ({label})" if label and is_sold_label(label) else "Chưa có đánh giá"
    if is_sold_label(label):
        return f"{score:g}/5 (sàn không ghi số lượt đánh giá; {label})"
    return f"{score:g}/5 ({label})" if label else f"{score:g}/5"
