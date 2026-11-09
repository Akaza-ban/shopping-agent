"""Luật guardrails giá (services/pricing/guardrails.py)."""

import pytest

from services.pricing import guardrails as g
from services.pricing.category_floors import FLOOR_FACTOR, MIN_SAMPLES, compute_floors


def test_compute_floors_from_real_prices():
    laptops = [("laptops", 10_000_000 + i * 500_000) for i in range(40)]
    rows = laptops + [("audio", 150_000)] * 5 + [("other", 29_000)] * 50 + [("phones", 0)] * 40
    floors = compute_floors(rows)
    assert floors == {"laptops": round(10_000_000 * FLOOR_FACTOR + 500_000 * 2 * FLOOR_FACTOR, -3)}
    # Ngành ít mẫu (audio), phụ kiện / hỗn hợp (other), giá 0 không tạo ngưỡng
    assert compute_floors([("audio", 1_000_000)] * (MIN_SAMPLES - 1)) == {}


@pytest.mark.parametrize(
    "price,category,rule",
    [
        (0, None, "missing"),
        (None, None, "missing"),
        (5_000, None, "below_floor"),
        (600_000_000, None, "above_ceiling"),
        (100_000, "laptops", "below_category_floor"),
        (300_000, "phones", "below_category_floor"),
    ],
)
def test_check_price_rejects(price, category, rule):
    v = g.check_price(price, category)
    assert not v.ok and v.rule == rule and v.reason


@pytest.mark.parametrize(
    "price,category",
    [
        (59_000, "other"),  # ốp lưng rẻ vẫn hợp lệ
        (139_000, None),
        (13_890_000, "laptops"),
        (1_479_000, "phones"),
    ],
)
def test_check_price_accepts(price, category):
    assert g.check_price(price, category).ok


def test_check_change():
    assert g.check_change(25_000_000, 30_000_000).ok  # giảm 17%
    assert g.check_change(2_000_000, 25_000_000).rule == "sudden_drop"  # giảm 92%
    assert g.check_change(28_000_000, 100_000).rule == "sudden_rise"
    assert g.check_change(25_000_000, None).ok


def test_confirmation_helpers():
    assert g.same_price(10_000_000, 10_150_000)  # lệch 1,5%
    assert not g.same_price(10_000_000, 10_500_000)
    assert not g.same_price(10_000_000, None)
    assert g.is_big_drop(6_000_000, 10_000_000)  # giảm 40%
    assert not g.is_big_drop(8_000_000, 10_000_000)


def _p(name, price, url="https://example.vn/x", **kw):
    return {"name": name, "currentPrice": price, "externalUrl": url, **kw}


def test_screen_products_drops_low_outliers_and_category_floor():
    products = [
        _p("Asus TUF Gaming A15 FA506NCQ", 27_990_000, "https://www.thegioididong.com/laptop/asus-tuf"),
        _p("Asus TUF Gaming A15 FA506NCQ", 100_000, "https://www.thegioididong.com/laptop/asus-tuf"),
        _p("Nồi chiên không dầu AVA 9 lít", 100_000),
        _p("Ốp lưng iPhone 15", 59_000),
    ]
    refs = {g.product_key("Nồi chiên không dầu AVA 9 lít"): [1_490_000]}
    kept, rejected = g.screen_products(products, refs)
    assert [p["currentPrice"] for p in kept] == [27_990_000, 59_000]
    assert {v.rule for _, v in rejected} == {"below_category_floor", "outlier_low"}


def test_screen_products_ignores_stale_query_label():
    # Sách bị crawler cũ gắn nhãn "laptop" theo câu hỏi -> không áp sàn giá laptop
    kept, rejected = g.screen_products([_p("Giúp Em Tìm Hiểu Chính Mình", 30_000, category="laptop")])
    assert kept and not rejected


def test_screen_products_keeps_higher_price_when_only_bad_reference():
    # Mốc tham chiếu duy nhất là giá rác 100.000 đ -> giá thật 28 triệu vẫn được giữ (chỉ loại giá THẤP bất thường)
    kept, _ = g.screen_products([_p("HP Victus 15", 27_990_000)], {g.product_key("HP Victus 15"): [100_000]})
    assert len(kept) == 1
