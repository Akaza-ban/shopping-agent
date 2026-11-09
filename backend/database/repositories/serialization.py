"""Chuyển giá trị cột sang dạng JSON trả cho API."""

from datetime import datetime


def iso(value: datetime | None) -> str | None:
    """Thời điểm dạng ISO 8601; None nếu cột trống."""
    return value.isoformat() if value else None
