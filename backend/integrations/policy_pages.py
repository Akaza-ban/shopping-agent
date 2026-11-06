"""Tải trang chính sách công khai của các nền tảng, lấy phần nội dung chính và chia thành đoạn để tra cứu."""
import re
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup, Tag

from integrations.platforms.errors import CRAWL_ERRORS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
}
CHUNK_CHARS = 700

POLICY_SOURCES: Dict[str, List[Dict[str, str]]] = {
    "tgdd": [{"doc_type": "return", "title": "Chính sách bảo hành, đổi trả sản phẩm",
              "url": "https://www.thegioididong.com/chinh-sach-bao-hanh-san-pham", "selector": "#help-main"}],
    "dmx": [{"doc_type": "return", "title": "Chính sách bảo hành, đổi trả sản phẩm",
             "url": "https://www.dienmayxanh.com/chinh-sach-bao-hanh-san-pham", "selector": "#help-main"}],
    "fpt-shop": [{"doc_type": "return", "title": "Chính sách đổi trả",
                  "url": "https://fptshop.com.vn/ho-tro/chinh-sach-doi-san-pham", "selector": "#article-content"}],
    "cellphones": [{"doc_type": "return", "title": "Chính sách hủy giao dịch, đổi trả hàng",
                    "url": "https://cellphones.com.vn/quy-che-hoat-dong-ung-dung-cellphones/chinh-sach-doi-tra",
                    "selector": "#pageBody"}],
}

_BLOCKS = ("p", "li", "h1", "h2", "h3", "h4", "h5", "tr", "div")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_lines(html: str, selector: str) -> List[str]:
    """Các dòng văn bản của vùng nội dung chính; mỗi hàng bảng thành một dòng 'ô | ô | ô'."""
    soup = BeautifulSoup(html, "html.parser")
    root: Optional[Tag] = soup.select_one(selector)
    if root is None:
        return []
    for t in root(["script", "style", "noscript", "svg", "img", "button", "form"]):
        t.decompose()
    lines: List[str] = []
    for el in root.find_all(_BLOCKS):
        if el.name == "tr":
            cells = [_clean(c.get_text(" ")) for c in el.find_all(["td", "th"])]
            line = " | ".join(c for c in cells if c)
        elif el.name == "div" and el.find(_BLOCKS):
            continue
        elif el.find_parent("tr") is not None or el.find_parent("li") is not None and el.name != "li":
            continue
        else:
            line = _clean(el.get_text(" "))
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return [l for l in lines if l.lower() not in ("xem nhanh",)]


def chunk_lines(lines: List[str], limit: int = CHUNK_CHARS) -> List[str]:
    """Ghép các dòng liền nhau thành đoạn khoảng `limit` ký tự; dòng ngắn kiểu tiêu đề đi kèm nội dung sau nó."""
    chunks: List[str] = []
    cur = ""
    for line in lines:
        if cur and len(cur) + len(line) + 1 > limit and len(cur) > 80:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


async def fetch_document(source: Dict[str, str], client: httpx.AsyncClient) -> Dict[str, object]:
    r = await client.get(source["url"])
    r.raise_for_status()
    lines = extract_lines(r.text, source["selector"])
    if sum(len(l) for l in lines) < 500:
        raise ValueError(f"không tìm thấy nội dung chính ({source['selector']})")
    return {**source, "lines": lines, "chunks": chunk_lines(lines)}


async def fetch_all(platform_ids: Optional[List[str]] = None) -> Dict[str, List[Dict[str, object]]]:
    """{platform_id: [tài liệu]}; nền tảng lỗi trả về danh sách rỗng kèm khóa 'error'."""
    out: Dict[str, List[Dict[str, object]]] = {}
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=25) as client:
        for pid, sources in POLICY_SOURCES.items():
            if platform_ids and pid not in platform_ids:
                continue
            docs = []
            for s in sources:
                try:
                    docs.append(await fetch_document(s, client))
                except CRAWL_ERRORS as e:
                    docs.append({**s, "error": str(e)})
            out[pid] = docs
    return out
