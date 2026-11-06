"""TGDĐ / ĐMX: giá đang hiển thị trên trang chi tiết và tìm theo số model khi trang tìm kiếm rỗng."""
import asyncio
import json

from integrations.platforms.mwg import TGDD, _token_pattern, parse_mwg_price


def _detail_page(shown: str, struck: str, jsonld_price: int) -> str:
    ld = {"@context": "https://schema.org", "@type": "Product", "name": "Máy giặt Aqua 7.2 kg",
          "offers": {"@type": "Offer", "price": jsonld_price, "priceCurrency": "VND"}}
    return f"""<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body>
      <div class="bg-error-50"><div class="gap-24px flex"><div class="flex flex-col">
        <span class="text-24 font-700 text-red-5">{shown}<!-- -->đ</span>
        <div class="flex gap-2"><del class="text-14 text-gray-5">{struck}<!-- -->đ</del><span class="text-red-5">-17%</span></div>
      </div></div></div></body></html>"""


def test_displayed_price_wins_over_jsonld():
    # JSON-LD ghi giá khu vực khác (4.550.000) - giá thật là số đỏ đang hiển thị
    assert parse_mwg_price(_detail_page("3.790.000", "4.550.000", 4550000)) == (3790000.0, 4550000.0)


def test_displayed_price_without_strikethrough():
    html = '<div><span class="text-24 text-red-5">25.490.000đ</span></div>'
    assert parse_mwg_price(html) == (25490000.0, 25490000.0)
    assert parse_mwg_price("<div>Liên hệ</div>") is None


def test_fetch_price_uses_displayed_price(monkeypatch):
    class Resp:
        status_code = 200
        text = _detail_page("3.790.000", "4.550.000", 4550000)

    class Client:
        async def get(self, url, headers=None):
            return Resp()

    offer = asyncio.run(TGDD.fetch_price(Client(), {"externalUrl": "https://www.thegioididong.com/may-giat/x"}))
    assert offer["currentPrice"] == 3790000.0 and offer["originalPrice"] == 4550000.0


def test_token_pattern_matches_model_numbers():
    assert _token_pattern("16").search("iPhone 16 128GB")
    assert not _token_pattern("16").search("iPhone 160")
    assert not _token_pattern("16").search("iPhone 16e")
    assert _token_pattern("9kg").search("LG Inverter 9 Kg FB1209S5W")
    assert _token_pattern("m4").search("MacBook Air M4 13 inch")


def test_model_query_falls_back_to_category_page(monkeypatch):
    """'iphone 16' ra trang rỗng -> bỏ dần từ cuối ('iphone' = trang danh mục), chỉ giữ thẻ có số 16."""
    calls = []
    catalog = [{"name": n} for n in ["iPhone 17 Pro 256GB", "iPhone 16 Plus 128GB", "iPhone 16 128GB", "iPhone 16e 128GB"]]

    async def fake_listing(client, query):
        calls.append(query)
        return list(catalog) if query == "iphone" else []

    monkeypatch.setattr(TGDD, "_fetch_listing", fake_listing)
    found = asyncio.run(TGDD._fetch_model(None, "iphone 16 plus"))
    assert calls == ["iphone 16 plus", "iphone 16", "iphone"]
    # Đủ số model "16"; khớp thêm chữ "plus" nên xếp trước; "16e" không phải iPhone 16
    assert [p["name"] for p in found] == ["iPhone 16 Plus 128GB", "iPhone 16 128GB"]


def test_query_without_model_number_is_not_broadened(monkeypatch):
    calls = []

    async def fake_listing(client, query):
        calls.append(query)
        return []

    monkeypatch.setattr(TGDD, "_fetch_listing", fake_listing)
    assert asyncio.run(TGDD._fetch_model(None, "máy giặt lg")) == []
    assert calls == ["máy giặt lg"]
