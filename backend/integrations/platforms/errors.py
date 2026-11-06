"""Ranh giới lỗi khi cào sàn / tải trang: lỗi mạng và lỗi đọc dữ liệu trang -> CrawlerError."""
from contextlib import contextmanager
from typing import Iterator

import httpx

from shared.exceptions import CrawlerError

# Lỗi mạng (httpx) và lỗi đọc dữ liệu do trang của sàn thay đổi cấu trúc:
# JSON hỏng (ValueError), thiếu khóa / phần tử (KeyError, IndexError), giá trị None (TypeError, AttributeError).
CRAWL_ERRORS = (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError)


@contextmanager
def crawling(source: str) -> Iterator[None]:
    """`with crawling("Tiki"): ...` - lỗi trong khối thuộc CRAWL_ERRORS được đổi thành CrawlerError(source)."""
    try:
        yield
    except CRAWL_ERRORS as e:
        raise CrawlerError(source, f"{type(e).__name__}: {e}") from e
