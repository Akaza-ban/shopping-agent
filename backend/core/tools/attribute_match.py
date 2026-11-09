"""Đối chiếu thông số kỹ thuật bắt buộc (VD GPU, RAM) với dữ liệu thu thập được, và ghi chú độ mới của dữ liệu.

Ghi chú (notes) được đưa vào prompt để Advisor không khẳng định điều chưa xác minh.
"""

import re
from datetime import UTC, datetime
from typing import Any

from services.catalog.ranker import verifiable_attributes
from shared.types import RawProduct

from ..state import UniversalSearchCriteria

STALE_AFTER_HOURS = 1
SHOW_DAYS_AFTER_HOURS = 48


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", "", s.lower())


def annotate(
    products: list[RawProduct], criteria: UniversalSearchCriteria | None, notes: list[str]
) -> list[RawProduct]:
    """Đưa sản phẩm xác nhận đúng thông số bắt buộc lên đầu; ghi chú khi không / chỉ một phần xác nhận được."""
    if not products or not criteria or not criteria.attributes:
        return products
    wanted = verifiable_attributes(criteria)
    if not wanted:
        return products

    verified, unverified = [], []
    for p in products:
        haystack = _norm(f"{p.get('name', '')} {p.get('specs', '')} {p.get('aiSummary', '')}")
        (verified if all(_norm(v) in haystack for v in wanted.values()) else unverified).append(p)

    wanted_text = ", ".join(f"{k}={v}" for k, v in wanted.items())
    if not verified:
        notes.append(
            f"KHÔNG sản phẩm nào xác nhận được yêu cầu kỹ thuật ({wanted_text}) từ tên/thông số thu thập được. "
            f"Không được khẳng định các sản phẩm dưới đây đáp ứng yêu cầu này."
        )
    elif unverified:
        notes.append(
            f"Chỉ {len(verified)}/{len(products)} sản phẩm xác nhận có {wanted_text} (xếp đầu danh sách); "
            f"các sản phẩm còn lại CHƯA xác minh được thông số này."
        )
    return verified + unverified


def _age_hours(raw: Any, now: datetime) -> float | None:
    """updatedAt (timestamp hoặc ISO) -> số giờ đã trôi qua; None nếu không đọc được."""
    try:
        ts = (
            datetime.fromtimestamp(float(raw), tz=UTC)
            if str(raw).replace(".", "").isdigit()
            else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        )
    except (ValueError, OSError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)  # DB lưu datetime.utcnow() không kèm múi giờ
    return (now - ts).total_seconds() / 3600


def freshness_note(products: list[RawProduct]) -> str | None:
    """Ghi chú độ mới nếu dữ liệu lấy từ cache / kho lưu (có updatedAt) và đã cũ hơn 1 giờ."""
    now = datetime.now(UTC)
    ages = [a for a in (_age_hours(p.get("updatedAt"), now) for p in products if p.get("updatedAt")) if a is not None]
    if not ages:
        return None
    oldest = max(ages)
    if oldest < STALE_AFTER_HOURS:
        return None
    age_text = f"{oldest:.0f} giờ" if oldest < SHOW_DAYS_AFTER_HOURS else f"{oldest / 24:.0f} ngày"
    return (
        f"Dữ liệu giá cũ nhất trong danh sách được cập nhật cách đây khoảng {age_text}; giá thực tế có thể đã thay đổi."
    )
