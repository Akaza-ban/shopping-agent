"""Ranh giới lỗi khi cào sàn / tải trang: lỗi mạng và lỗi đọc dữ liệu trang -> CrawlerError."""
from contextlib import contextmanager
from typing import Iterator

import httpx

from shared.exceptions import CrawlerError

CRAWL_ERRORS = (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError)


@contextmanager
def crawling(source: str) -> Iterator[None]:
    """`with crawling("Tiki"): ...` - lỗi trong khối thuộc CRAWL_ERRORS được đổi thành CrawlerError(source)."""
    try:
        yield
    except CRAWL_ERRORS as e:
        raise CrawlerError(source, f"{type(e).__name__}: {e}") from e
