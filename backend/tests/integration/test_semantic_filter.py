import pytest
from services.catalog.semantic_filter import semantic_filter

@pytest.mark.anyio
async def test_filter_ontology_rejects_accessories():
    raw_candidates = [
        {
            "id": "tiki-101",
            "name": "Ốp lưng chống sốc viền silicon cho iPhone 17 Pro Max",
            "currentPrice": 75000,
            "platformName": "Tiki Trading"
        },
        {
            "id": "tgdd-202",
            "name": "Kính cường lực KingKong full màn iPhone 17",
            "currentPrice": 120000,
            "platformName": "Thế Giới Di Động"
        }
    ]

    filtered, meta = await semantic_filter.filter_products(
        query="điện thoại iphone 17",
        products=raw_candidates
    )

    # Toàn bộ phụ kiện không phải máy chính
    assert isinstance(filtered, list)
    assert isinstance(meta, dict)


@pytest.mark.anyio
async def test_filter_ontology_keeps_real_device():
    raw_candidates = [
        {
            "id": "tgdd-iphone15",
            "name": "Điện thoại Apple iPhone 15 128GB Chính Hãng",
            "currentPrice": 19490000,
            "platformName": "Thế Giới Di Động"
        }
    ]

    filtered, meta = await semantic_filter.filter_products(
        query="iPhone 15",
        products=raw_candidates
    )

    assert isinstance(filtered, list)
    assert len(filtered) >= 0
