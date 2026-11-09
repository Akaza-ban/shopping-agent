"""Ngành hàng của một sản phẩm theo bảng quy đổi danh mục đã học (category_resolver); chưa biết -> "other"."""

from collections.abc import Mapping
from typing import Any

from services.catalog.category_resolver import category_resolver
from shared.categories import FALLBACK


def known_category(product: Mapping[str, Any]) -> str | None:
    mapping = category_resolver.lookup(product)
    return mapping.category if mapping else None


def is_accessory(product: Mapping[str, Any]) -> bool | None:
    mapping = category_resolver.lookup(product)
    return mapping.is_accessory if mapping else None


def categorize(product: Mapping[str, Any]) -> str:
    return known_category(product) or FALLBACK
