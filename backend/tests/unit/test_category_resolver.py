"""
Quy đổi danh mục của sàn -> ngành hàng chuẩn (không có bảng viết tay):
- Đọc được các dạng đầu ra của LLM (mảng object, object theo khóa, phần mô tả thay cho mã).
- Danh mục mới gom lại hỏi LLM một lần, lưu kết quả; lần sau chỉ tra bảng, không hỏi lại.
"""

import asyncio
import sys

from services.catalog.category_resolver import CategoryResolver, parse_classification

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def test_parse_classification_accepts_model_output_variants():
    rows = parse_classification(
        '```json\n[{"key": "tgdd:dtdd", "category": "phones", "accessory": false},'
        ' {"key": "tgdd:op-lung", "category": "other", "accessory": true},'
        ' {"key": "x:la", "category": "không-có-mã"}]\n```'
    )
    assert rows["tgdd:dtdd"].category == "phones" and rows["tgdd:op-lung"].is_accessory
    assert "x:la" not in rows  # mã ngoài danh sách chuẩn bị bỏ
    by_key = parse_classification('{"dmx:tivi": {"category": "home_appliances", "accessory": false}}')
    assert by_key["dmx:tivi"].category == "home_appliances"
    # Model trả phần mô tả / số ít thay cho mã
    labels = parse_classification(
        '[{"key": "a", "category": "điện thoại / máy tính bảng"}, {"key": "b", "category": "laptop"}]'
    )
    assert (labels["a"].category, labels["b"].category) == ("phones", "laptops")
    assert parse_classification("không phải JSON") == {}


class _Repo:
    def __init__(self):
        self.saved = []

    async def all(self):
        return [{"source_key": "tgdd:dtdd", "category": "phones", "is_accessory": False, "decided_by": "manual"}]

    async def save(self, rows):
        self.saved += rows


def test_resolve_asks_once_and_remembers(monkeypatch):
    repo = _Repo()
    resolver = CategoryResolver(repository=repo)
    calls = []

    class _Model:
        async def ainvoke(self, messages):
            calls.append(messages[-1].content)
            return type(
                "R", (), {"content": '[{"key": "dmx:may-giat", "category": "home_appliances", "accessory": false}]'}
            )()

    monkeypatch.setattr(
        "services.catalog.category_resolver.get_chat_model", lambda temperature=0.0, fast=False: _Model()
    )
    phone = {"name": "iPhone 16", "externalUrl": "https://www.thegioididong.com/dtdd/iphone-16"}
    washer = {"name": "Máy giặt LG 9 kg", "externalUrl": "https://www.dienmayxanh.com/may-giat/lg-9kg"}

    asyncio.run(resolver.resolve([phone, washer, dict(washer, name="Máy giặt Aqua")]))
    assert resolver.lookup(phone).category == "phones"  # nạp từ bảng đã lưu, không hỏi LLM
    assert resolver.lookup(washer).category == "home_appliances"
    assert len(calls) == 1 and "dmx:may-giat" in calls[0] and "tgdd:dtdd" not in calls[0]
    assert "Máy giặt Aqua" in calls[0]  # gửi kèm tên sản phẩm mẫu làm căn cứ
    assert [r["source_key"] for r in repo.saved] == ["dmx:may-giat"]

    asyncio.run(resolver.resolve([washer]))
    assert len(calls) == 1  # lần sau chỉ tra bảng


def test_product_noun_learned_and_applied():
    """Tên loại hiển thị học cùng lần quy đổi; chỉ ghép khi tên sản phẩm chưa có (thay cho bảng FPT_NAME_PREFIX)."""
    from services.catalog.category_resolver import with_noun

    rows = parse_classification(
        '[{"key": "fpt-shop:Điện máy/Máy giặt", "category": "home_appliances", "noun": "Máy giặt"},'
        ' {"key": "fpt-shop:Điện thoại/iPhone (IOS)", "category": "phones", "noun": ""}]'
    )
    assert rows["fpt-shop:Điện máy/Máy giặt"].noun == "Máy giặt" and rows["fpt-shop:Điện thoại/iPhone (IOS)"].noun == ""
    assert with_noun("LG Inverter 9 kg", "Máy giặt") == "Máy giặt LG Inverter 9 kg"
    assert with_noun("Máy giặt LG Inverter 9 kg", "Máy giặt") == "Máy giặt LG Inverter 9 kg"  # không lặp
    assert with_noun("iPhone 16", "") == "iPhone 16"


def test_crawl_applies_noun_to_names(_offline_category_resolver):
    from core.tools.ecom_search import EcomSearchTool

    _offline_category_resolver.remember({"fpt-shop:Điện máy/Máy giặt": ("home_appliances", False, "Máy giặt")})
    washer = {
        "id": "fpt-1",
        "name": "LG Inverter 9 kg",
        "platform": "fpt-shop",
        "sourceCategoryPath": "fpt-shop:Điện máy/Máy giặt",
        "externalUrl": "https://fptshop.com.vn/may-giat/lg",
    }
    lists = {"fpt-shop": [washer]}
    asyncio.run(EcomSearchTool(platforms=[])._apply_categories(lists, None))
    assert lists["fpt-shop"][0]["name"] == "Máy giặt LG Inverter 9 kg"
    assert lists["fpt-shop"][0]["category"] == "home_appliances"
