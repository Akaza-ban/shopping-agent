import asyncio
import sys
import os

# Set UTF-8 encoding for Windows stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.tools.ecom_search import EcomSearchTool

async def main():
    tool = EcomSearchTool()
    queries = ["điện thoại", "iphone 15", "samsung galaxy s24"]
    for q in queries:
        print(f"\n==================== SEARCHING: '{q}' ====================")
        results = await tool.run(query=q, limit=8, force_refresh=True)
        print(f"Total returned: {len(results)}")
        for r in results:
            print(f"- [{r.get('platform')}] {r.get('name')} | {r.get('currentPrice', 0):,.0f} đ | {r.get('categoryName')}")

if __name__ == "__main__":
    asyncio.run(main())
