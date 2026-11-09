"""Ghi log mỗi request: method, đường dẫn, mã trả về, thời gian xử lý.

Viết dạng ASGI thuần (không dùng BaseHTTPMiddleware) để không chen vào luồng SSE của /chat/stream.
"""

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("request")

SLOW_REQUEST_SECONDS = 5.0


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = 500

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            elapsed = time.perf_counter() - start
            level = logging.WARNING if elapsed >= SLOW_REQUEST_SECONDS else logging.INFO
            logger.log(level, "%s %s -> %s (%.0f ms)", scope["method"], scope["path"], status, elapsed * 1000)
