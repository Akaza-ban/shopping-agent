import pytest

from core.state import UniversalSearchCriteria
from core.tools.ecom_search import EcomSearchTool


@pytest.mark.anyio
async def test_search_platforms_concurrent():
    tool = EcomSearchTool()
    criteria = UniversalSearchCriteria(
        category="laptop",
        category_name="Laptop",
        min_price=10000000,
        max_price=30000000,
        cleaned_query="laptop",
        target_platforms=["all"],
    )
    products = await tool.run(query="laptop", criteria=criteria, limit=6)

    assert len(products) > 0
    for p in products:
        assert p["platform"] in ["tiki", "tgdd", "dmx"]
        assert p["currentPrice"] > 0
        assert len(p["name"]) > 0
        assert p["externalUrl"].startswith("http")
