"""Dữ liệu cá nhân đồng bộ giữa các thiết bị (hội thoại, sản phẩm đã lưu, lịch sử, tùy chọn giao diện)."""

import json
from typing import Any

from database.models import UserModel
from database.repositories import user_repository
from shared.exceptions import InvalidInputError, NotFoundError, PayloadTooLargeError

USER_DATA_KEYS = {"conversations", "saved-products", "activities", "search-history", "preferences"}
MAX_USER_DATA_BYTES = 2 * 1024 * 1024


def _check_key(key: str) -> None:
    if key not in USER_DATA_KEYS:
        raise NotFoundError("Khóa dữ liệu không hợp lệ.")


async def get(user: UserModel, key: str) -> dict[str, Any]:
    _check_key(key)
    return {"key": key, "value": await user_repository.get_data(user.id, key)}


async def save(user: UserModel, key: str, body: bytes) -> dict[str, Any]:
    """`body` là nội dung request dạng JSON {"value": ...}."""
    _check_key(key)
    if len(body) > MAX_USER_DATA_BYTES:
        raise PayloadTooLargeError("Dữ liệu quá lớn.")
    try:
        value: Any = json.loads(body).get("value")
    except (ValueError, AttributeError) as e:  # JSON hỏng / không phải đối tượng JSON
        raise InvalidInputError("Dữ liệu không phải JSON hợp lệ.") from e
    await user_repository.set_data(user.id, key, value)
    return {"key": key, "saved": True}
