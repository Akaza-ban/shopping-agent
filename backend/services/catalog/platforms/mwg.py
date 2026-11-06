"""Thế Giới Di Động & Điện Máy Xanh (cùng hệ thống MWG): trang tìm kiếm HTML và trang chi tiết HTML."""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from core.state import UniversalSearchCriteria
from services.catalog.platforms.base import PlatformAdapter
from services.catalog.platforms.common import (
    BROWSER_HEADERS, MAX_SPEC_ITEMS, PAGE_HEADERS, canonical_spec_label, clean_text, page_offer, parse_availability,
    query_candidates, within_price, broadened_note, first_hit,
)

logger = logging.getLogger("platforms.mwg")

# Giá dạng "27.990.000đ" / "27.990.000₫"
MWG_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3}){1,3})\s*(?:₫|đ)")


def _price(text: str) -> float:
    m = MWG_PRICE_RE.search(text or "")
    return float(m.group(1).replace(".", "")) if m else 0.0


def parse_mwg_listing(html: str, platform: str, domain: str) -> List[Dict[str, Any]]:
    """Danh sách sản phẩm từ HTML trang danh mục/tìm kiếm TGDĐ & ĐMX (giao diện Next.js 2026)."""
    soup = BeautifulSoup(html, "html.parser")
    items, seen_roots = [], set()
    for img in soup.find_all("img", alt=True):
        if len(img.get("alt", "").strip()) < 4:
            continue
        root = _card_root(img)
        if root is None or id(root) in seen_roots:
            continue
        seen_roots.add(id(root))
        item = _parse_card(img, root, platform, domain)
        if item:
            items.append(item)
    return items


def _card_root(img) -> Optional[Any]:
    """Thẻ sản phẩm chứa ảnh: phần tử cha gần nhất (tối đa 8 cấp) có giá; bỏ khối danh sách chứa nhiều sản phẩm."""
    node = img
    for _ in range(8):
        node = node.parent
        if node is None or node.name in ("body", "html"):
            return None
        if MWG_PRICE_RE.search(node.get_text(" ", strip=True)):
            alts = {i.get("alt", "").strip() for i in node.find_all("img", alt=True) if len(i.get("alt", "").strip()) >= 4}
            return node if len(alts) <= 2 else None
    return None


def _parse_card(img, root, platform: str, domain: str) -> Optional[Dict[str, Any]]:
    href = _card_href(root, domain)
    current, original = _card_prices(root)
    if not href or current <= 0:
        return None
    title_a = root.find("a", title=True)
    spaced_text = root.get_text(" ", strip=True)
    rating_m = re.search(r"(?<![\d.])([1-5](?:\.\d)?)\s*•", spaced_text)
    sold_m = re.search(r"Đã bán\s*([\d.,]+\s*k?)", spaced_text)
    chips = [c.get_text(" ", strip=True) for c in root.select("[class*=text-nowrap]")]
    return {
        "id": f"{platform}-{href.rstrip('/').split('/')[-1]}",
        "name": ((title_a.get("title") if title_a else "") or img.get("alt", "")).strip(),
        "href": href,
        "currentPrice": current,
        "originalPrice": original,
        "discountPercent": _card_discount(root, current, original),
        "rating": float(rating_m.group(1)) if rating_m else None,
        "sold": f"Đã bán {sold_m.group(1).strip()}" if sold_m else None,
        "specs": " - ".join([c for c in chips if c and not MWG_PRICE_RE.search(c)][:6]),
        "image": _card_image(img),
    }


def _card_href(root, domain: str) -> Optional[str]:
    hrefs = [a.get("href", "") for a in root.find_all("a", href=True)]
    hrefs = [h for h in hrefs if (h.startswith("/") and len(h) > 1) or h.startswith(domain)]
    if not hrefs:
        return None
    return hrefs[0] if hrefs[0].startswith("http") else f"{domain}{hrefs[0]}"


def _card_prices(root) -> Tuple[float, float]:
    """(giá bán, giá gốc): ưu tiên giá màu đỏ, không có thì giá lớn nhất ngoài <del> (bỏ "Quà ..."); giá gốc ở <del>."""
    price_el = root.select_one("[class*=text-red-7]")
    current = _price(price_el.get_text()) if price_el else 0.0
    if current <= 0:
        candidates = [_price(s) for s in root.find_all(string=MWG_PRICE_RE)
                      if not s.find_parent("del") and "quà" not in s.lower()]
        current = max(candidates) if candidates else 0.0
    original = max([p for p in (_price(d.get_text()) for d in root.find_all("del")) if p > current], default=current)
    return current, original


def _card_discount(root, current: float, original: float) -> int:
    m = re.search(r"-\s*(\d{1,2})\s*%", root.get_text("", strip=True))
    if m:
        return int(m.group(1))
    return int(round((1 - current / original) * 100)) if original > current else 0


def _card_image(img) -> str:
    """Ảnh thật của thẻ (bỏ ảnh giữ chỗ dạng data:, thêm https: cho link //)."""
    thumb = img.get("data-src") or img.get("src") or ""
    if thumb.startswith("data:"):
        thumb = img.get("data-src") or ""
    return f"https:{thumb}" if thumb.startswith("//") else thumb


def parse_mwg_detail(html: str) -> Dict[str, Any]:
    """Đọc trang chi tiết TGDĐ/ĐMX: bảng thông số + câu bảo hành/đổi trả."""
    soup = BeautifulSoup(html, "html.parser")
    specs: Dict[str, str] = {}
    for li in soup.find_all("li"):
        children = [c for c in li.find_all(recursive=False) if clean_text(c.get_text())]
        if len(children) < 2:
            continue
        label = clean_text(children[0].get_text())
        if not label.endswith(":") or len(label) > 60:
            continue
        value = clean_text(" ".join(c.get_text(" ", strip=True) for c in children[1:]))
        if not value or len(value) > 200:
            continue
        key = canonical_spec_label(label)
        if key not in specs:
            specs[key] = value
        if len(specs) >= MAX_SPEC_ITEMS:
            break

    for tag in soup(["script", "style"]):
        tag.decompose()
    text = clean_text(soup.get_text(" ", strip=True))

    sentence_end = r"(?<!\d)\.|\.(?!\d)"
    warranty = None
    m = re.search(rf"Bảo hành chính hãng\s+(.{{3,80}}?)(?=\s+(?:Xem|Hư gì|Bộ sản phẩm|Kèm theo)|,|{sentence_end}|$)", text)
    if m:
        warranty = f"Bảo hành chính hãng {m.group(1).strip()}"

    return_policy = None
    m = re.search(rf"(Hư gì đổi nấy\s+.{{3,60}}?)(?=\s+(?:Bảo hành|Xem|Bộ sản phẩm|Kèm theo)|{sentence_end}|$)", text)
    if m:
        return_policy = m.group(1).strip()

    return {"specs": specs, "warranty": warranty, "returnPolicy": return_policy}


def parse_mwg_price(html: str) -> Optional[Tuple[float, float]]:
    """
    (giá bán, giá gốc) đang hiển thị trên trang chi tiết: số màu đỏ có giá gạch ngang (<del>) cạnh bên.
    Không dùng JSON-LD vì trang ghi giá của khu vực giá khác (thường cao hơn giá đang bán online).
    """
    soup = BeautifulSoup(html, "html.parser")
    reds = [el for el in soup.select("[class*=text-red]") if MWG_PRICE_RE.fullmatch(el.get_text("", strip=True))]
    for el in reds:
        box = el.parent
        for _ in range(2):
            struck = box.find("del") if box else None
            if struck:
                current = _price(el.get_text())
                return current, max(_price(struck.get_text()), current)
            box = box.parent if box else None
    if reds:
        current = _price(reds[0].get_text())
        return current, current
    return None


def _token_pattern(word: str) -> re.Pattern:
    """Một từ của từ khóa trong tên sản phẩm: "9kg" khớp "9 Kg", "m4" khớp "M4"; "16" không khớp "160" hay "16e"."""
    parts = re.findall(r"\d+(?:[.,]\d+)?|[^\W\d_]+", word)
    return re.compile(r"(?<![\w.])" + r"\s?".join(map(re.escape, parts)) + r"(?!\w)", re.IGNORECASE)


def _narrow_to_model(items: List[Dict[str, Any]], words: List[str], model: List[re.Pattern]) -> List[Dict[str, Any]]:
    """Thẻ có đủ các số model; thẻ khớp nhiều từ của từ khóa hơn (hãng, dòng máy) xếp trước."""
    matched = [it for it in items if all(p.search(it["name"]) for p in model)]
    others = [_token_pattern(w) for w in words if not re.search(r"\d", w)]
    return sorted(matched, key=lambda it: -sum(bool(p.search(it["name"])) for p in others))


class MwgAdapter(PlatformAdapter):
    def __init__(self, id: str, name: str, domain: str, aliases, badge_color: str, badge_bg: str,
                 warranty: str, delivery_tag: str):
        self.id, self.name, self.domain = id, name, domain
        self.hosts = (domain.split("//", 1)[-1].removeprefix("www."),)
        self.aliases = tuple(aliases)
        self.badge_color, self.badge_bg = badge_color, badge_bg
        self.warranty, self.delivery_tag = warranty, delivery_tag

    def parse_listing(self, html: str) -> List[Dict[str, Any]]:
        return parse_mwg_listing(html, self.id, self.domain)

    async def search(self, keyword, criteria, limit, notes, user_query=""):
        """Thử nhiều biến thể từ khóa cho tới khi trang trả về sản phẩm (xem query_candidates)."""
        headers = {**BROWSER_HEADERS, "Referer": f"{self.domain}/"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0) as client:
            raw, used = await first_hit(query_candidates(keyword, criteria), lambda q: self._fetch_model(client, q))
        if not raw:
            logger.info(f"[{self.name}] Không có sản phẩm nào cho '{keyword}' "
                        f"(sàn không bán mặt hàng này, hoặc trang đã đổi giao diện - xem test RUN_LIVE_TESTS).")
            return []
        note = broadened_note(self.name, keyword, used)
        if note:
            notes.append(note)
        return [self._to_product(it, criteria) for it in raw if within_price(it["currentPrice"], criteria)][:limit]

    async def _fetch_model(self, client, query: str) -> List[Dict[str, Any]]:
        """
        Từ khóa có số model ("iphone 16", "tủ lạnh samsung 236 lít") thường ra trang tìm kiếm rỗng
        (kết quả do JavaScript nạp sau). Khi đó bỏ dần từ cuối tới khi sàn chuyển sang trang danh mục
        có sẵn thẻ sản phẩm, rồi chỉ giữ thẻ có đủ các số model.
        """
        items = await self._fetch_listing(client, query)
        words = query.split()
        model = [_token_pattern(w) for w in words if re.search(r"\d", w)]
        if items or not model:
            return items
        for n in range(len(words) - 1, 0, -1):
            items = await self._fetch_listing(client, " ".join(words[:n]))
            if items:
                return _narrow_to_model(items, words, model)
        return []

    async def _fetch_listing(self, client, query: str) -> List[Dict[str, Any]]:
        """Sản phẩm trên trang tìm kiếm; trang ~600KB đôi khi bị ngắt giữa chừng nên thử lại 1 lần."""
        for attempt in range(2):
            try:
                resp = await client.get(f"{self.domain}/tim-kiem", params={"key": query})
                return self.parse_listing(resp.text) if resp.status_code == 200 else []
            except httpx.HTTPError as e:
                logger.warning(f"Lỗi kết nối {self.name} (lần {attempt + 1}) cho '{query}': {e}")
                await asyncio.sleep(0.5)
        return []

    def _to_product(self, it: Dict[str, Any], criteria) -> Dict[str, Any]:
        specs = it["specs"]
        return {
            **self.product_base(criteria),
            "id": it["id"],
            "name": it["name"],
            "category": criteria.category if criteria else "all",
            "aiMatchScore": 95 if (it["rating"] or 0) >= 4.5 else 85,
            "originalPrice": it["originalPrice"],
            "currentPrice": it["currentPrice"],
            "discountPercent": it["discountPercent"],
            "rating": it["rating"] if it["rating"] is not None else 0.0,
            "reviewsCount": it["sold"] or "Chưa có đánh giá",
            "sku": f"{self.id.upper()}-{it['id'].split('-', 1)[-1]}",
            "image": it["image"],
            "specs": specs,
            "aiSummary": f"Sản phẩm thực tế tại {self.name}: {it['name']}." + (f" {specs}" if specs else ""),
            "externalUrl": it["href"],
        }

    async def fetch_detail(self, client, product):
        url = product.get("externalUrl") or ""
        if not url.startswith("http"):
            return None
        resp = await client.get(url, headers=PAGE_HEADERS)
        return parse_mwg_detail(resp.text) if resp.status_code == 200 else None

    async def fetch_price(self, client, product):
        url = product.get("externalUrl") or ""
        if not url.startswith("http"):
            return None
        resp = await client.get(url, headers=PAGE_HEADERS)
        if resp.status_code != 200:
            return None
        shown = parse_mwg_price(resp.text)
        if not shown:
            return page_offer(resp.text)
        return {"currentPrice": shown[0], "originalPrice": shown[1], "inStock": parse_availability(resp.text)}

    def category_source(self, product):
        """Đoạn đầu đường dẫn là danh mục của TGDĐ / ĐMX ("/dtdd/", "/may-giat/")."""
        url = product.get("externalUrl") or ""
        if not self.owns_url(url):
            return None
        slug = urlparse(url).path.strip("/").split("/")[0].lower()
        return (f"{self.id}:{slug}", f"danh mục /{slug}/ của {self.name}") if slug else None


TGDD = MwgAdapter(
    "tgdd", "Thế Giới Di Động", "https://www.thegioididong.com", ("tgdd", "thế giới di động", "thegioididong"),
    "#EEC708", "rgba(255, 212, 0, 0.15)", "Chính hãng TGDĐ (1 đổi 1 tháng đầu)", "Giao nhanh 2h",
)
DMX = MwgAdapter(
    "dmx", "Điện Máy Xanh", "https://www.dienmayxanh.com", ("dmx", "điện máy xanh", "dienmayxanh"),
    "#0083d1", "rgba(0, 131, 209, 0.15)", "Chính hãng ĐMX (Lắp đặt tận nhà)", "Giao hàng & Lắp đặt",
)
