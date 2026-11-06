import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.tools.ecom_search import EcomSearchTool
from core.state import UniversalSearchCriteria

async def main():
    tool = EcomSearchTool()

    test_cases = [
        {
            "name": "Case 1: Tìm điện thoại (is_accessory=False, target_entity='điện thoại')",
            "query": "samsung galaxy s24",
            "criteria": UniversalSearchCriteria(
                category="phones",
                target_entity="điện thoại",
                is_accessory=False,
                cleaned_query="samsung galaxy s24"
            )
        },
        {
            "name": "Case 2: Tìm iPhone (is_accessory=False, target_entity='điện thoại')",
            "query": "iphone 15",
            "criteria": UniversalSearchCriteria(
                category="phones",
                target_entity="điện thoại",
                is_accessory=False,
                cleaned_query="iphone 15"
            )
        },
        {
            "name": "Case 3: Tìm Tivi (Ngành hàng khác! target_entity='tivi', is_accessory=False)",
            "query": "Sony 55 inch",
            "criteria": UniversalSearchCriteria(
                category="home_appliances",
                target_entity="tivi",
                is_accessory=False,
                cleaned_query="Sony 55 inch"
            )
        },
        {
            "name": "Case 4: Tìm phụ kiện đích danh (is_accessory=True, target_entity='ốp lưng')",
            "query": "ốp lưng iphone 15",
            "criteria": UniversalSearchCriteria(
                category="phones",
                target_entity="ốp lưng",
                is_accessory=True,
                cleaned_query="ốp lưng iphone 15"
            )
        }
    ]

    for tc in test_cases:
        print(f"\n==================== {tc['name']} ====================")
        results = await tool.run(
            query=tc["query"],
            criteria=tc["criteria"],
            limit=5,
            force_refresh=True
        )
        print(f"Tổng kết quả: {len(results)}")
        for r in results:
            print(f"- [{r.get('platform')}] {r.get('name')} | {r.get('currentPrice', 0):,.0f} đ")

if __name__ == "__main__":
    asyncio.run(main())
