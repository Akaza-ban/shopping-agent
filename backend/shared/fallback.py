"""Bỏ qua một số loại lỗi đã biết (ghi log) để chạy tiếp bằng giá trị mặc định."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

ErrorTypes = type[BaseException] | tuple[type[BaseException], ...]


@contextmanager
def fallback(errors: ErrorTypes, message: str, logger: logging.Logger, level: int = logging.WARNING) -> Iterator[None]:
    """Chỉ nuốt đúng `errors`; lỗi khác (lỗi lập trình) vẫn được ném ra.

    cached = None
    with fallback(DatabaseError, "Lỗi kiểm tra cache SQLite", logger):
        cached = await product_repository.get_cached_search(...)
    """
    try:
        yield
    except errors as e:
        logger.log(level, "%s: %s", message, e)
