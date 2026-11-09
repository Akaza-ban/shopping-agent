"""Khóa so khớp cùng một sản phẩm giữa các bản ghi / các lần cào."""

import re


def product_key(name: str) -> str:
    """Khóa so khớp cùng sản phẩm giữa các bản ghi (tên viết thường, gộp khoảng trắng)."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())
