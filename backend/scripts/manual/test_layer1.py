import asyncio
import httpx
import sys
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def check():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        # Check Tiki with 'điện thoại samsung galaxy s24'
        res = await client.get("https://tiki.vn/api/v2/products", params={"q": "điện thoại samsung galaxy s24", "limit": 6})
        print("=== TIKI: 'điện thoại samsung galaxy s24' ===")
        for it in res.json().get("data", []):
            print(f"Tiki: {it.get('name')} | Cat: {it.get('primary_category_name')}")

        # Check TGDD
        resp = await client.get("https://www.thegioididong.com/tim-kiem?key=điện thoại samsung galaxy s24")
        soup = BeautifulSoup(resp.text, "html.parser")
        print("\n=== TGDD: 'điện thoại samsung galaxy s24' ===")
        for item in soup.select("li.item[data-id]:not(.merge__item)")[:6]:
            a = item.select_one("a.main-contain, a[href]")
            if a:
                print(f"TGDD: {a.get('data-name')} | Href: {a.get('href')}")

if __name__ == "__main__":
    asyncio.run(check())
