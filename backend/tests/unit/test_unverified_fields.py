"""Không có dữ liệu thật thì để trống: trợ lý nói "Chưa rõ" thay vì tự điền bảo hành / đánh giá / vận chuyển."""

from core.agents.advisor_context import format_product
from core.agents.advisor_fallback import link_review
from core.state import ProductItemModel
from services.catalog.data_processor import data_processor

BASE = {
    "id": "p1",
    "name": "Laptop Test",
    "platform": "tiki",
    "platformName": "Tiki",
    "originalPrice": 1e7,
    "currentPrice": 1e7,
}


def test_defaults_are_unknown_not_invented():
    p = ProductItemModel(**BASE)
    assert p.rating == 0.0
    assert p.reviewsCount == ""
    assert p.warranty is None
    assert p.deliveryTag is None


def test_legacy_placeholders_from_storage_are_dropped():
    p = ProductItemModel(
        **BASE, warranty="Chính hãng 12 tháng", deliveryTag="TikiNOW Giao 2h", reviewsCount="Chính hãng"
    )
    assert p.warranty is None
    assert p.deliveryTag is None
    assert p.reviewsCount == ""


def test_real_values_are_kept():
    p = ProductItemModel(**BASE, warranty="Bảo hành chính hãng 24 tháng", reviewsCount="12 đánh giá")
    assert p.warranty == "Bảo hành chính hãng 24 tháng"
    assert p.reviewsCount == "12 đánh giá"


def test_processor_does_not_fill_warranty_or_delivery():
    out = data_processor.process_product({**BASE, "reviewsCount": "0 đánh giá"})
    assert out["warranty"] is None
    assert out["deliveryTag"] is None
    assert out["reviewsCount"] == "Chưa có đánh giá"


def test_advisor_context_says_unknown():
    text = format_product(1, ProductItemModel(**BASE))
    assert "Bảo hành: Chưa rõ" in text
    assert "Vận chuyển: Chưa rõ" in text
    assert "Chưa có đánh giá" in text


def test_link_fallback_makes_no_unbacked_claims():
    text = link_review(ProductItemModel(**BASE, externalUrl="https://tiki.vn/x"))
    assert "rất cạnh tranh" not in text
    assert "nguồn gốc phân phối rõ ràng" not in text
    assert "Bảo hành:** Chưa rõ" in text
    assert "5/5" not in text
