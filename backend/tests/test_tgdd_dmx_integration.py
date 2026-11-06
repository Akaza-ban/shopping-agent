import sys
import io
import asyncio
import json

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.main import app
from core.tools.ecom_search import EcomSearchTool

client = TestClient(app)


def test_direct_tools():
    print("\n--- 1. TEST DIRECT ECOM_SEARCH TOOL ---")
    tool = EcomSearchTool()
    
    # Test TGDD
    tgdd_items = asyncio.run(tool.run(query="iphone", platform="tgdd", limit=3))
    print(f"TGDD count: {len(tgdd_items)}")
    for item in tgdd_items:
        print(f"  [{item['platform'].upper()}] {item['name'][:40]} | {item['currentPrice']:,.0f} đ | {item['externalUrl']}")
    assert len(tgdd_items) > 0
    assert tgdd_items[0]["platform"] == "tgdd"
    
    # Test DMX
    dmx_items = asyncio.run(tool.run(query="tu lanh toshiba", platform="dmx", limit=3))
    print(f"\nDMX count: {len(dmx_items)}")
    for item in dmx_items:
        print(f"  [{item['platform'].upper()}] {item['name'][:40]} | {item['currentPrice']:,.0f} đ | {item['externalUrl']}")
    assert len(dmx_items) > 0
    assert dmx_items[0]["platform"] == "dmx"

def test_api_endpoints():
    print("\n--- 2. TEST FASTAPI PRODUCTS SEARCH ENDPOINT ---")
    # TGDD endpoint
    res_tgdd = client.get("/api/v1/products/search?q=macbook&platform=tgdd&limit=3")
    assert res_tgdd.status_code == 200
    data_tgdd = res_tgdd.json()
    print(f"API TGDD returned {data_tgdd['total']} items for query '{data_tgdd['query']}'")
    assert data_tgdd["total"] > 0
    
    # DMX endpoint
    res_dmx = client.get("/api/v1/products/search?q=may giat&platform=dmx&limit=3")
    assert res_dmx.status_code == 200
    data_dmx = res_dmx.json()
    print(f"API DMX returned {data_dmx['total']} items for query '{data_dmx['query']}'")
    assert data_dmx["total"] > 0
    
    # All platforms
    res_all = client.get("/api/v1/products/search?q=laptop&platform=all&limit=6")
    assert res_all.status_code == 200
    data_all = res_all.json()
    platforms_present = {p["platform"] for p in data_all["data"]}
    print(f"API ALL returned {data_all['total']} items. Platforms present: {platforms_present}")
    assert data_all["total"] > 0

def test_chat_platform_routing():
    print("\n--- 3. TEST CHAT BOT TARGET PLATFORM RECOGNITION ---")
    
    # TGDD Chat
    req_tgdd = {"message": "Tìm điện thoại samsung tại thế giới di động"}
    res = client.post("/api/v1/chat", json=req_tgdd)
    assert res.status_code == 200
    chat_data = res.json()
    print("Chat TGDD status:", res.status_code)
    print("Found products count:", len(chat_data["products"]))
    if chat_data["products"]:
        for p in chat_data["products"][:3]:
            print(f"  * [{p['platform']}] {p['name'][:40]} - {p['currentPrice']:,.0f} đ")
        assert any(p["platform"] == "tgdd" for p in chat_data["products"])

    # DMX Chat
    req_dmx = {"message": "Tìm tủ lạnh inverter tại điện máy xanh"}
    res_dmx = client.post("/api/v1/chat", json=req_dmx)
    assert res_dmx.status_code == 200
    chat_dmx_data = res_dmx.json()
    print("\nChat DMX status:", res_dmx.status_code)
    print("Found products count:", len(chat_dmx_data["products"]))
    if chat_dmx_data["products"]:
        for p in chat_dmx_data["products"][:3]:
            print(f"  * [{p['platform']}] {p['name'][:40]} - {p['currentPrice']:,.0f} đ")
        assert any(p["platform"] == "dmx" for p in chat_dmx_data["products"])

if __name__ == "__main__":
    test_direct_tools()
    test_api_endpoints()
    test_chat_platform_routing()
    print("\n ALL TGDD & DMX INTEGRATION TESTS PASSED 100%!")
