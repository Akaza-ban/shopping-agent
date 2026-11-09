"""Chống SSRF (chạy offline, DNS và HTTP đều giả):
- check_public_url chặn link không phải http(s) và host trỏ vào mạng nội bộ.
- fetch_text kiểm tra lại từng bước chuyển hướng và bỏ trang quá lớn.
- Sàn chỉ đọc giá / chi tiết từ link thuộc chính sàn đó.
- Link trang lạ không được lưu vào kho RAG chung.
"""

import asyncio
import ipaddress
import socket

import httpx
import pytest

from core.tools import url_extractor
from integrations import safe_http
from integrations.platforms import get_platform
from shared.exceptions import InvalidInputError

FAKE_DNS = {
    "localhost": "127.0.0.1",
    "shop.example": "93.184.216.34",
    "inside.example": "10.0.0.5",
}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    async def resolve(host, port):
        if host in FAKE_DNS:
            return {FAKE_DNS[host]}
        try:
            return {str(ipaddress.ip_address(host))}
        except ValueError:
            raise socket.gaierror(host) from None

    monkeypatch.setattr(safe_http, "_resolve", resolve)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost:8000/docs",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
        "http://inside.example/x",
        "file:///etc/passwd",
        "ftp://shop.example/x",
        "khong-phai-link",
        "http://khong-ton-tai.example/",
    ],
)
def test_blocks_internal_or_invalid_urls(url):
    with pytest.raises(InvalidInputError):
        asyncio.run(safe_http.check_public_url(url))


def test_allows_public_url():
    asyncio.run(safe_http.check_public_url("https://shop.example/san-pham"))


def test_fetch_text_blocks_redirect_to_internal_host():
    hits = []

    def handler(request):
        hits.append(str(request.url))
        if request.url.host == "shop.example":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
        return httpx.Response(200, text="bí mật")

    text = asyncio.run(safe_http.fetch_text("https://shop.example/p", {}, 5, transport=httpx.MockTransport(handler)))
    assert text is None and hits == ["https://shop.example/p"]


def test_fetch_text_follows_public_redirect_and_limits_size():
    def handler(request):
        if request.url.path == "/cu":
            return httpx.Response(301, headers={"location": "/moi"})
        if request.url.path == "/lon":
            return httpx.Response(200, content=b"x" * 2000)
        return httpx.Response(200, text="<html>ok</html>")

    transport = httpx.MockTransport(handler)
    assert asyncio.run(safe_http.fetch_text("https://shop.example/cu", {}, 5, transport=transport)) == "<html>ok</html>"
    assert (
        asyncio.run(safe_http.fetch_text("https://shop.example/lon", {}, 5, max_bytes=1000, transport=transport))
        is None
    )


@pytest.mark.parametrize("platform_id", ["tgdd", "dmx", "fpt-shop", "cellphones"])
def test_platform_never_fetches_foreign_host(platform_id):
    class Client:
        async def get(self, url, headers=None):
            raise AssertionError(f"không được gọi {url}")

    platform = get_platform(platform_id)
    for url in (
        "http://127.0.0.1/x",
        "https://trang-gia.example/p",
        "https://thegioididong.com.evil.example/p",
        "https://www.thegioididong.com@127.0.0.1/p",
    ):
        product = {"id": "x", "externalUrl": url}
        assert asyncio.run(platform.fetch_price(Client(), product)) is None
        assert asyncio.run(platform.fetch_detail(Client(), product)) is None


def test_foreign_link_is_not_stored_in_rag(monkeypatch):
    item = {
        "id": "parsed-1",
        "name": "Máy lạ",
        "platform": "all",
        "platformName": "Website",
        "currentPrice": 5_000_000,
        "originalPrice": 5_000_000,
        "externalUrl": "https://shop.example/may",
        "category": "all",
    }
    stored = []

    async def read_link(url):
        return dict(item)

    async def apply_category(product):
        return None

    async def store(product):
        stored.append(product)

    tool = url_extractor.UrlExtractorTool()
    monkeypatch.setattr(tool, "_read_link", read_link)
    monkeypatch.setattr(tool, "_apply_category", apply_category)
    monkeypatch.setattr(tool, "_store_in_rag", store)
    monkeypatch.setattr(url_extractor.data_processor, "process_product", lambda p: dict(p))
    monkeypatch.setattr(
        url_extractor.price_guardrails,
        "check_price",
        lambda price, category: type("Verdict", (), {"ok": True, "reason": ""})(),
    )

    result = asyncio.run(tool.run("https://shop.example/may"))
    assert result["name"] == "Máy lạ" and stored == []


def test_parse_link_rejects_internal_url():
    with pytest.raises(InvalidInputError):
        asyncio.run(url_extractor.UrlExtractorTool().run("http://169.254.169.254/latest/meta-data"))
