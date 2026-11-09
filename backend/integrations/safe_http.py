"""Tải trang theo link người dùng đưa vào mà không để server bị lợi dụng gọi vào mạng nội bộ (SSRF).

    check_public_url()  link phải là http(s) và mọi IP của host đều là IP công khai
    fetch_text()        tải trang: tự theo redirect (kiểm tra lại từng bước), giới hạn kích thước

Còn hở: DNS rebinding (host trả IP công khai lúc kiểm tra, IP nội bộ lúc kết nối). Muốn chặn hẳn phải
tự viết transport cho httpx để kết nối đúng IP đã kiểm tra.
"""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import httpx

from shared.exceptions import InvalidInputError

logger = logging.getLogger("safe_http")

MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 5
BLOCKED_URL = "Link không hợp lệ hoặc trỏ tới địa chỉ nội bộ."


async def _resolve(host: str, port: int) -> set:
    """Các IP của host (tách riêng để test thay bằng DNS giả)."""
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return {info[4][0] for info in infos}


async def check_public_url(url: str) -> None:
    """InvalidInputError nếu link không phải http(s) hoặc host trỏ tới IP nội bộ / loopback / link-local."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise InvalidInputError(BLOCKED_URL)
    try:
        ips = await _resolve(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except (OSError, UnicodeError, ValueError) as e:  # gaierror là OSError; port sai -> ValueError
        raise InvalidInputError(BLOCKED_URL) from e
    if not ips or not all(ipaddress.ip_address(ip.split("%")[0]).is_global for ip in ips):
        raise InvalidInputError(BLOCKED_URL)


async def _read_body(resp: httpx.Response, max_bytes: int) -> str | None:
    """Nội dung trả về đã giải mã; None nếu vượt `max_bytes` (dừng đọc ngay, không tải hết)."""
    chunks, size = [], 0
    async for chunk in resp.aiter_bytes():
        size += len(chunk)
        if size > max_bytes:
            logger.warning(f"Trang quá lớn (> {max_bytes} byte), bỏ qua: {resp.url}")
            return None
        chunks.append(chunk)
    return b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")


async def fetch_text(
    url: str,
    headers: dict[str, str],
    timeout: float,
    max_bytes: int = MAX_PAGE_BYTES,
    max_redirects: int = MAX_REDIRECTS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str | None:
    """Nội dung trang; None nếu link / redirect bị chặn, lỗi mạng, mã trả về khác 200 hoặc trang quá lớn."""
    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=timeout, follow_redirects=False, transport=transport
        ) as client:
            for _ in range(max_redirects + 1):
                await check_public_url(url)
                async with client.stream("GET", url) as resp:
                    if resp.is_redirect and resp.headers.get("location"):
                        url = urljoin(url, resp.headers["location"])
                        continue
                    return await _read_body(resp, max_bytes) if resp.status_code == 200 else None
            logger.warning(f"Quá nhiều lần chuyển hướng: {url}")
            return None
    except InvalidInputError:
        logger.warning(f"Chặn tải link nội bộ / không hợp lệ: {url}")
        return None
    except httpx.HTTPError as e:
        logger.warning(f"Lỗi tải trang {url}: {e}")
        return None
