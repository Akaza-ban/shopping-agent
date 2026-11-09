"""Một cấu hình SSL dùng chung cho mọi httpx.AsyncClient gọi ra ngoài.

httpx tạo SSL context mới cho mỗi client nếu không truyền `verify`: khoảng 170-200 ms chạy đồng bộ, chặn vòng sự kiện,
nên các sàn được cào "song song" thực ra lần lượt bắt đầu chậm hơn nhau. Dùng: httpx.AsyncClient(verify=ssl_context()).
"""

import functools
import ssl

import httpx


@functools.cache
def ssl_context() -> ssl.SSLContext:
    return httpx.create_ssl_context()
