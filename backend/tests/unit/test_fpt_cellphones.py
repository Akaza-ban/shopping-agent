"""
Kiểm thử offline FPT Shop và CellphoneS:
- Đọc kết quả tìm kiếm FPT Shop từ dữ liệu RSC nhúng trong trang, kèm danh mục ngành / loại / nhóm do FPT gán.
- Đọc kết quả GraphQL advanced_search của CellphoneS; special_price = 0 là không giảm giá; nhận ra máy cũ.
- Khóa danh mục do sàn cung cấp; bỏ phụ kiện (theo bảng quy đổi), máy cũ khi người dùng không hỏi.
"""
import asyncio
import json
import os
import sys

import pytest

from core.state import UniversalSearchCriteria
from core.tools.ecom_search import EcomSearchTool
from integrations.platforms.cellphones import CellphonesAdapter, parse_cellphones_search
from integrations.platforms.fpt import parse_fpt_search
from services.catalog.categories import categorize
from integrations.platforms.fpt import FptAdapter

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _fpt_page(items):
    # JSON gọn (không dấu cách) như dữ liệu thật của trang
    payload = json.dumps({"product": {"name": "từ khóa", "result": {"totalCount": len(items), "items": items}}},
                         ensure_ascii=False, separators=(",", ":"))
    # Trang Next.js đẩy dữ liệu RSC dưới dạng chuỗi JSON đã escape, có thể tách thành nhiều đoạn
    half = len(payload) // 2
    chunks = [json.dumps(payload[:half], ensure_ascii=False)[1:-1], json.dumps(payload[half:], ensure_ascii=False)[1:-1]]
    return "<html>" + "".join(f'<script>self.__next_f.push([1,"{c}"])</script>' for c in chunks) + "</html>"


FPT_ITEMS = [
    {"code": "001", "displayName": "LG Inverter 9 kg FB1209S6O", "slug": "may-giat/lg-inverter-9-kg-fb1209s6o",
     "originalPrice": 9590000, "currentPrice": 7990000, "discountPercentage": 17, "averageScore": None,
     "industry": {"name": "Điện máy"}, "productType": {"name": "Máy giặt"},
     "sold": {"realQuantity": 0}, "image": {"src": "https://cdn2.fptshop.com.vn/a.jpg"},
     "keySellingPoints": [{"title": "Inverter", "description": "tiết kiệm điện"}]},
    {"code": "002", "displayName": "iPhone 16", "slug": "dien-thoai/iphone-16", "originalPrice": 25690000,
     "currentPrice": 24990000, "discountPercentage": 3, "averageScore": 5, "sold": {"realQuantity": 27737},
     "image": {"src": "https://cdn2.fptshop.com.vn/b.jpg"}, "keySellingPoints": []},
    {"code": "003", "displayName": "Ốp lưng MagSafe iPhone 16", "slug": "phu-kien/op-lung-magsafe-iphone-16",
     "originalPrice": 990000, "currentPrice": 790000, "image": {}},
    {"code": "004", "displayName": "Hết giá", "slug": "dien-thoai/het-gia", "currentPrice": 0},
]


def test_parse_fpt_search_reads_embedded_results():
    items = parse_fpt_search(_fpt_page(FPT_ITEMS))
    assert [i["id"] for i in items] == ["fpt-001", "fpt-002", "fpt-003"]  # sản phẩm không có giá bị bỏ
    washer, phone = items[0], items[1]
    assert washer["name"] == "LG Inverter 9 kg FB1209S6O"  # tên loại được ghép sau, ở bước quy đổi danh mục
    assert washer["categoryPath"] == "fpt-shop:Điện máy/Máy giặt"
    assert washer["href"] == "https://fptshop.com.vn/may-giat/lg-inverter-9-kg-fb1209s6o"
    assert (washer["currentPrice"], washer["originalPrice"], washer["discountPercent"]) == (7990000, 9590000, 17)
    assert washer["specs"] == "Inverter tiết kiệm điện" and washer["rating"] == 0
    assert phone["name"] == "iPhone 16" and phone["sold"] == "Đã bán 27737"
    assert parse_fpt_search("<html>không có dữ liệu</html>") == []


def test_category_source_keys():
    """Khóa danh mục do chính sàn cung cấp (để quy đổi một lần), không phải bảng viết tay."""
    fpt, cps = FptAdapter(), CellphonesAdapter()
    assert fpt.category_source({"sourceCategoryPath": "fpt-shop:Phụ kiện/Tai nghe"})[0] == "fpt-shop:Phụ kiện/Tai nghe"
    # Sản phẩm lưu từ trước chưa có danh mục FPT -> đoạn đầu đường dẫn
    assert fpt.category_source({"externalUrl": "https://fptshop.com.vn/robot-hut-bui/ecovacs-t30c"})[0] == "fpt-shop:/robot-hut-bui"
    assert fpt.category_source({"externalUrl": "https://www.thegioididong.com/dtdd/x"}) is None
    assert cps.category_source({"sourceCategoryPath": "cellphones:Âm thanh/Tai nghe/Sony"})[0] == "cellphones:Âm thanh/Tai nghe"
    assert cps.category_source({"sourceCategoryPath": "1/2/1815/8215"}) is None  # đường dẫn Tiki không bị hiểu nhầm


CPS_DATA = {"data": {"advanced_search": {"meta": {"total": 4}, "products": [
    {"product_id": 1, "name": "iPhone 16 128GB | Chính hãng VN/A", "url_path": "iphone-16.html", "price": 24990000.0,
     "special_price": 0, "thumbnail": "/i/p/iphone-16.png",
     "category_objects": [{"name": "Root"}, {"name": "Điện thoại"}, {"name": "Apple"}]},
    {"product_id": 2, "name": "iPhone 16 Pro 128GB - Cũ Đẹp", "url_path": "iphone-16-pro-cu-dep.html",
     "price": 28990000.0, "special_price": 21590000.0, "thumbnail": "/i/p/b.png",
     "category_objects": [{"name": "Hàng cũ"}, {"name": "iPhone cũ"}]},
    {"product_id": 5, "name": "iPhone 16 Pro Max 512GB", "url_path": "iphone-16-pro-max-512gb-cu-da-kich-hoat.html",
     "price": 30000000.0, "special_price": 27000000.0, "thumbnail": "", "category_objects": [{"name": "Hàng cũ"}]},
    {"product_id": 3, "name": "Ốp lưng iPhone 16", "url_path": "op-lung.html", "price": 300000.0,
     "special_price": 250000.0, "thumbnail": "", "category_objects": [{"name": "Root"}, {"name": "Phụ kiện"}]},
    {"product_id": 4, "name": "Tai nghe Sony WH-CH730N", "url_path": "sony-wh-ch730n.html", "price": 3190000.0,
     "special_price": 2990000.0, "thumbnail": "/s/o/sony.png",
     "category_objects": [{"name": "Âm thanh"}, {"name": "Tai nghe"}, {"name": "Phụ kiện Sony"}]},
]}}}


def test_parse_cellphones_search():
    items = parse_cellphones_search(CPS_DATA)
    iphone, used, used_unlabeled, case, headphone = items
    assert used_unlabeled["used"] and used_unlabeled["name"] == "iPhone 16 Pro Max 512GB (cũ)"
    assert iphone["name"] == "iPhone 16 128GB" and iphone["href"] == "https://cellphones.com.vn/iphone-16.html"
    assert (iphone["currentPrice"], iphone["discountPercent"]) == (24990000.0, 0)  # special_price 0 = không giảm
    assert iphone["image"] == "https://cdn2.cellphones.com.vn/358x/media/catalog/product/i/p/iphone-16.png"
    assert iphone["categoryPath"] == "cellphones:Điện thoại/Apple" and not iphone["used"]
    assert used["used"] and used["currentPrice"] == 21590000.0 and used["discountPercent"] == 26
    assert headphone["categoryPath"] == "cellphones:Âm thanh/Tai nghe/Phụ kiện Sony"
    assert parse_cellphones_search({"errors": [{"message": "x"}]}) == []


class _FakeResponse:
    status_code = 200

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_search_cellphones_skips_used_and_accessories(monkeypatch, _offline_category_resolver):
    import httpx

    async def fake_post(self, url, json=None):
        return _FakeResponse(CPS_DATA)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    _offline_category_resolver.remember({
        "cellphones:Điện thoại/Apple": ("phones", False), "cellphones:Hàng cũ/iPhone cũ": ("phones", False),
        "cellphones:Hàng cũ": ("phones", False), "cellphones:Phụ kiện": ("other", True),
        "cellphones:Âm thanh/Tai nghe": ("audio", False),
    })
    cps = CellphonesAdapter()
    tool = EcomSearchTool(platforms=[cps])
    normal, _ = asyncio.run(tool._crawl("iphone 16", None, "cellphones", 10, []))
    used = asyncio.run(cps.search("iphone 16 cũ", None, 10, []))
    accessory, _ = asyncio.run(tool._crawl("ốp lưng iphone 16", UniversalSearchCriteria(is_accessory=True), "cellphones", 10, []))
    assert {p["id"] for p in normal} == {"cps-1", "cps-4"}  # bỏ máy cũ (adapter) và ốp lưng (bảng quy đổi)
    assert {p["id"]: p["category"] for p in normal}["cps-4"] == "audio"
    assert categorize({"platform": "cellphones", "sourceCategoryPath": "cellphones:Âm thanh/Tai nghe/Phụ kiện Sony"}) == "audio"
    assert {"cps-2", "cps-5"} <= {p["id"] for p in used}
    assert "cps-3" in [p["id"] for p in accessory]


DETAIL_HTML = """<html><head>
<script type="application/ld+json">{"@type": "Organization", "name": "FPT Shop"}</script>
<script type="application/ld+json" id="product-schema">{"@context": "https://schema.org", "@type": "Product",
 "name": "LG Inverter 9 kg", "additionalProperty": [
   {"@type": "PropertyValue", "name": "Khối lượng", "value": "9 Kg"},
   {"@type": "PropertyValue", "name": "Công nghệ tiết kiệm điện", "value": "Inverter"}],
 "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.9", "reviewCount": "89"}}</script>
</head><body>Sản phẩm gợi ý: Khối lượng giặt 12 Kg</body></html>"""


def test_parse_jsonld_detail_and_merge():
    from services.catalog.enricher import ProductEnricher
    from integrations.platforms.common import parse_jsonld_detail
    detail = parse_jsonld_detail(DETAIL_HTML)
    assert detail["specs"] == {"Khối lượng": "9 Kg", "Công nghệ tiết kiệm điện": "Inverter"}
    assert (detail["rating"], detail["reviewsCount"]) == (4.9, 89)
    assert parse_jsonld_detail("<html></html>")["specs"] == {}

    product = {"id": "cps-1", "platform": "cellphones", "rating": 0.0, "reviewsCount": "Chưa có đánh giá",
               "specs": "Chip A18", "externalUrl": "https://cellphones.com.vn/x.html"}
    merged = ProductEnricher.merge_detail(product, detail)
    assert merged["rating"] == 4.9 and merged["reviewsCount"] == "89 đánh giá"
    assert merged["specs"]["Khối lượng"] == "9 Kg" and merged["specs"]["Tóm tắt"] == "Chip A18"
    assert ProductEnricher._cache_key(product) == "https://cellphones.com.vn/x.html"


def test_used_query_searches_raw_user_text_first(monkeypatch):
    import httpx
    sent = []

    async def fake_post(self, url, json=None):
        sent.append(json["query"])
        return _FakeResponse(CPS_DATA)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    asyncio.run(CellphonesAdapter().search("điện thoại iphone 16 cũ", None, 10, [], user_query="iphone 16 cũ"))
    assert '"iphone 16 cũ"' in sent[0]  # không có "điện thoại" do từ khóa crawler tự thêm


# Trang thật: phát hiện sớm khi sàn đổi giao diện / API (chạy với RUN_LIVE_TESTS=1)
live = pytest.mark.skipif(not os.getenv("RUN_LIVE_TESTS"), reason="Đặt RUN_LIVE_TESTS=1 để chạy test gọi trang thật")


@live
@pytest.mark.parametrize("platform", ["fpt-shop", "cellphones"])
def test_live_search_and_detail(platform):
    from services.catalog.enricher import product_enricher

    async def scenario():
        products, counts = await EcomSearchTool()._crawl("iphone 16", None, platform, 4, [])
        enriched = await product_enricher.enrich(products[:2], max_items=2, budget_seconds=15)
        return products, counts, enriched

    products, counts, enriched = asyncio.run(scenario())
    assert counts[platform] > 0, f"{platform}: không đọc được kết quả tìm kiếm (trang/API đã đổi?)"
    assert all(p["currentPrice"] > 1_000_000 and p["externalUrl"].startswith("https://") for p in products)
    assert any(p.get("detailFetched") for p in enriched), f"{platform}: không đọc được thông số trang chi tiết"
