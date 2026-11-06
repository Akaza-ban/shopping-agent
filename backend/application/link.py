"""Đọc thông tin sản phẩm từ link người dùng dán vào (API riêng, ngoài khung chat)."""
from typing import Any, Dict

from core.tools.url_extractor import UrlExtractorTool
from shared.exceptions import CrawlerError, InvalidInputError

extractor = UrlExtractorTool()


async def parse_link(url: str) -> Dict[str, Any]:
    url = (url or "").strip()
    if not url:
        raise InvalidInputError("Vui lòng cung cấp đường dẫn URL hợp lệ.")
    try:
        product = await extractor.run(url=url)
    except (InvalidInputError, CrawlerError) as e:
        raise InvalidInputError(f"Không thể bóc tách liên kết: {e}") from e
    return {"status": "success", "product": product}
