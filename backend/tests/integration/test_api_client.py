import sys
import io
import json

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_single_platforms():
    print("=" * 65)
    print("1. TEST API TÌM KIẾM CHỈ TRÊN SÀN TIKI (platform=tiki)")
    print("=" * 65)
    res_tiki = client.get("/api/v1/products/search?q=laptop&platform=tiki&limit=4")
    print(f"Status: {res_tiki.status_code}")
    data_tiki = res_tiki.json()
    print(f"Sàn: {data_tiki.get('platform')} | Tổng số sản phẩm: {data_tiki.get('total', 0)}")
    for p in data_tiki.get("data", []):
        print(f" - [{p['platform'].upper():6}] {p['name'][:42]} | Giá: {p['currentPrice']:>11,.0f} đ | {p['platformName']}")

    print("\n" + "=" * 65)
    print("2. TEST API TÌM KIẾM CHỈ TRÊN SÀN LAZADA (platform=lazada)")
    print("=" * 65)
    res_laz = client.get("/api/v1/products/search?q=laptop&platform=lazada&limit=4")
    print(f"Status: {res_laz.status_code}")
    data_laz = res_laz.json()
    print(f"Sàn: {data_laz.get('platform')} | Tổng số sản phẩm: {data_laz.get('total', 0)}")
    for p in data_laz.get("data", []):
        print(f" - [{p['platform'].upper():6}] {p['name'][:42]} | Giá: {p['currentPrice']:>11,.0f} đ | {p['platformName']}")

    print("\n" + "=" * 65)
    print("3. TEST API TÌM KIẾM CẢ 2 SÀN ĐAN XEN (platform=all)")
    print("=" * 65)
    res_all = client.get("/api/v1/products/search?q=chảo chống dính&platform=all&limit=4")
    print(f"Status: {res_all.status_code}")
    data_all = res_all.json()
    print(f"Sàn: {data_all.get('platform')} | Tổng số sản phẩm: {data_all.get('total', 0)}")
    for p in data_all.get("data", []):
        print(f" - [{p['platform'].upper():6}] {p['name'][:42]} | Giá: {p['currentPrice']:>11,.0f} đ | {p['platformName']}")

    print("\n" + "=" * 65)
    print("4. TEST CHAT API VỚI YÊU CẦU SÀN CỤ THỂ (Target Platform Extraction)")
    print("=" * 65)
    payload = {
        "session_id": "test-session-lazada-only",
        "message": "Tìm trên lazada cho tôi chảo chống dính thương hiệu lớn dưới 500k",
        "platform": "lazada"
    }
    print(f"Gửi Chat: '{payload['message']}'...")
    res_chat = client.post("/api/v1/chat", json=payload)
    print(f"Status: {res_chat.status_code}")
    chat_data = res_chat.json()
    criteria = chat_data.get("criteria", {})
    print(f"-> Sàn nhận diện (target_platforms): {criteria.get('target_platforms')}")
    print(f"-> Sản phẩm trả về ({len(chat_data.get('products', []))} items):")
    for p in chat_data.get("products", []):
        print(f"   * [{p['platform'].upper()}] {p['name'][:45]} | {p['currentPrice']:>10,.0f} đ")

if __name__ == "__main__":
    test_single_platforms()
