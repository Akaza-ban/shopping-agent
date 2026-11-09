"""
Kiểm thử kho chính sách (chạy offline): DB SQLite tạm, LLM giả.
- Nạp chính sách mẫu một lần; nạp lại không nhân đôi dữ liệu, sửa nội dung thì tách lại đoạn văn.
- Điều khoản riêng của ngành hàng được ưu tiên hơn bản 'all'.
- Tra cứu trả về điều khoản, đoạn trích liên quan và tóm tắt; LLM lỗi thì dùng tóm tắt dựng sẵn.
"""

import asyncio
import sys
from types import SimpleNamespace

import httpx
import openai
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import application.policies as policy_service
from database.connection import Base
from database.models import PolicyChunkModel, PolicyTermModel
from database.repositories.policy_repo import PolicyRepository
from services.policy.seed import POLICY_SEED, document_text

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def _setup(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'policies.db'}")
    async with engine.begin() as conn:
        from database import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repo = PolicyRepository(factory)
    monkeypatch.setattr(policy_service, "policy_repository", repo)
    from database.repositories.product_repo import ProductRepository

    monkeypatch.setattr(policy_service, "product_repository", ProductRepository(factory))  # kho sản phẩm trống
    return engine, factory, repo


async def _count(factory, model):
    async with factory() as s:
        return await s.scalar(select(func.count()).select_from(model))


def test_seed_is_idempotent_and_rechunks_on_change(tmp_path, monkeypatch):
    async def scenario():
        engine, factory, repo = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        await policy_service.ensure_seeded()
        terms, chunks = await _count(factory, PolicyTermModel), await _count(factory, PolicyChunkModel)

        tiki = POLICY_SEED[0]
        changed = {**tiki["terms"], "return_window_days": 15, "exceptions": []}
        await repo.upsert_platform_policy(tiki, changed, document_text(tiki["name"], changed))
        after = await repo.list_policies(["tiki"])
        tiki_chunks = [c["text"] for c in await repo.list_chunks(["tiki"])]
        await engine.dispose()
        return terms, chunks, after, tiki_chunks

    terms, chunks, after, tiki_chunks = asyncio.run(scenario())
    assert terms == len(POLICY_SEED)
    assert chunks > len(POLICY_SEED)
    assert after[0]["returnWindowDays"] == 15
    assert any("15 ngày" in c for c in tiki_chunks)
    assert not any(c.startswith("Lưu ý") for c in tiki_chunks)


def test_category_specific_terms_override_default(tmp_path, monkeypatch):
    async def scenario():
        engine, _, repo = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        tgdd = POLICY_SEED[1]
        await repo.upsert_platform_policy(
            tgdd,
            {**tgdd["terms"], "return_window_days": 7},
            document_text(tgdd["name"], tgdd["terms"]),
            category="Thời trang",
        )
        default = await repo.list_policies(["tgdd"])
        fashion = await repo.list_policies(["tgdd"], "Thời trang")
        everything = await repo.list_policies()
        await engine.dispose()
        return default, fashion, everything

    default, fashion, everything = asyncio.run(scenario())
    assert default[0]["returnWindowDays"] == 30 and default[0]["category"] == "all"
    assert fashion[0]["returnWindowDays"] == 7
    assert [p["platformId"] for p in everything] == [p["id"] for p in POLICY_SEED]


class _FakeLLM:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.prompt = reply, error, None

    async def ainvoke(self, messages):
        self.prompt = messages[-1].content
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.reply)


def test_lookup_uses_llm_with_grounded_data(tmp_path, monkeypatch):
    llm = _FakeLLM("Tiki có lợi nhất vì trả hàng miễn phí.")
    monkeypatch.setattr(policy_service, "get_chat_model", lambda temperature=0.0, fast=False: llm)

    async def scenario():
        engine, _, _ = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        result = await policy_service.lookup("MacBook Air M3 lỗi có được đổi không", ["tiki", "tgdd"])
        await engine.dispose()
        return result

    result = asyncio.run(scenario())
    assert [p["platformId"] for p in result["policies"]] == ["tiki", "tgdd"]
    assert result["summary"] == "Tiki có lợi nhất vì trả hàng miễn phí." and result["usedLlm"] is True
    assert result["excerpts"] and all(e["platformId"] in ("tiki", "tgdd") for e in result["excerpts"])
    assert "Thế Giới Di Động" in llm.prompt and "FPT Shop" not in llm.prompt


def test_lookup_falls_back_when_llm_fails(tmp_path, monkeypatch):
    # Lỗi nhà cung cấp trả về khi hết quota (HTTP 429)
    quota = openai.RateLimitError(
        "quota", response=httpx.Response(429, request=httpx.Request("POST", "https://llm.test")), body=None
    )
    llm = _FakeLLM(error=quota)
    monkeypatch.setattr(policy_service, "get_chat_model", lambda temperature=0.0, fast=False: llm)

    async def scenario():
        engine, _, _ = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        vi = await policy_service.lookup("iPhone 16", ["tgdd", "tiki"])
        en = await policy_service.lookup("iPhone 16", ["tiki"], language="en")
        none = await policy_service.lookup("iPhone 16", [])
        await engine.dispose()
        return vi, en, none

    vi, en, none = asyncio.run(scenario())
    assert vi["usedLlm"] is False and "Tiki Trading" in vi["summary"] and "miễn phí trả hàng" in vi["summary"]
    assert en["summary"].startswith("Tiki Trading: returns within 30 days")  # một nền tảng: nói về đúng nền tảng đó
    assert none["policies"] == [] and none["summary"] == ""


def test_extract_main_content_and_chunk():
    from integrations.policy_pages import chunk_lines, extract_lines

    html = """<html><body><nav>Trang chủ Điện thoại Laptop</nav>
    <div id="help-main"><h2>1. Đổi trả</h2><p>Lỗi nhà sản xuất được 1 đổi 1 trong 30 ngày.</p>
    <table><tr><th>Thời gian</th><th>Phí</th></tr><tr><td>Tháng đầu</td><td>20% giá trị hóa đơn</td></tr></table>
    <ul><li>Còn hộp, phụ kiện</li><li>Không trầy xước</li></ul><script>var x = 1;</script></div>
    <footer>Bản quyền</footer></body></html>"""
    lines = extract_lines(html, "#help-main")
    assert lines == [
        "1. Đổi trả",
        "Lỗi nhà sản xuất được 1 đổi 1 trong 30 ngày.",
        "Thời gian | Phí",
        "Tháng đầu | 20% giá trị hóa đơn",
        "Còn hộp, phụ kiện",
        "Không trầy xước",
    ]
    assert extract_lines(html, "#khong-co") == []
    chunks = chunk_lines(["a" * 90, "b" * 50, "c" * 600, "d" * 10], limit=200)
    assert chunks == ["a" * 90 + "\n" + "b" * 50, "c" * 600, "d" * 10]


def test_official_documents_replace_summary_excerpts(tmp_path, monkeypatch):
    async def scenario():
        engine, _, repo = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        url = "https://www.thegioididong.com/chinh-sach-bao-hanh-san-pham"
        first = await repo.upsert_document(
            "tgdd",
            "return",
            "Chính sách đổi trả",
            url,
            ["Hoàn tiền tháng đầu: phí 20% giá trị hóa đơn.", "Bảo hành 12 tháng tại cửa hàng."],
        )
        again = await repo.upsert_document(
            "tgdd",
            "return",
            "Chính sách đổi trả",
            url,
            ["Hoàn tiền tháng đầu: phí 20% giá trị hóa đơn.", "Bảo hành 12 tháng tại cửa hàng."],
        )
        chunks = await repo.list_chunks(["tgdd", "tiki"])
        excerpts = await policy_service.find_excerpts("hoàn tiền mất phí bao nhiêu", ["tgdd", "tiki"], per_platform=1)
        await engine.dispose()
        return first, again, chunks, excerpts

    first, again, chunks, excerpts = asyncio.run(scenario())
    assert first is True and again is False
    assert {c["url"] for c in chunks if c["platformId"] == "tgdd"} == {
        "https://www.thegioididong.com/chinh-sach-bao-hanh-san-pham"
    }
    assert any(c["platformId"] == "tiki" for c in chunks)  # Tiki chưa có trang gốc -> dùng bản tóm tắt
    assert [e["platformId"] for e in excerpts] == ["tgdd", "tiki"]
    assert "20%" in excerpts[0]["text"]


def test_parse_extracted_terms_and_flag_unsupported_numbers():
    import pytest

    from services.policy.extractor import parse_terms, unsupported_numbers

    raw = """```json
{"return_window_days": "365", "free_return": false, "return_conditions": "Còn hộp",
 "return_shipping_fee": null, "refund_time": "Tháng đầu phí 20% giá trị hóa đơn",
 "defect_exchange": "1 đổi 1 trong 30 ngày", "warranty_handling": "Cửa hàng", "exceptions": ["Phí 25%"], "evidence": []}
```"""
    terms = parse_terms(raw)
    assert terms["return_window_days"] == 365 and terms["return_conditions"] == ["Còn hộp"]
    assert terms["return_shipping_fee"] == ""
    page = "1 ĐỔI 1 trong 30 ngày. Tháng đầu tiên: phí 20% giá trị hóa đơn."
    assert unsupported_numbers(terms, page) == ["25%", "365"]
    with pytest.raises(ValueError):
        parse_terms('{"return_window_days": 9999}')
    with pytest.raises(ValueError):
        parse_terms("không có json")


def test_verified_flag_follows_source_document(tmp_path, monkeypatch):
    async def scenario():
        engine, _, repo = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        await repo.upsert_document("tgdd", "return", "Chính sách", "https://tgdd.vn/cs", ["Phí 20% tháng đầu."])
        doc_id = next(d["id"] for d in await repo.official_documents() if d["platformId"] == "tgdd")
        tgdd = POLICY_SEED[1]["terms"]
        await repo.upsert_terms("tgdd", {**tgdd, "refund_time": "Tháng đầu phí 20%"}, document_id=doc_id)
        policies = {p["platformId"]: p for p in await repo.list_policies(["tgdd", "tiki"])}
        await engine.dispose()
        return policies

    policies = asyncio.run(scenario())
    assert policies["tgdd"]["verified"] is True and policies["tgdd"]["refundTime"] == "Tháng đầu phí 20%"
    assert policies["tgdd"]["policyUrl"] == "https://tgdd.vn/cs"
    assert policies["tiki"]["verified"] is False


def test_scope_follows_where_the_product_is_sold(tmp_path, monkeypatch):
    from database.repositories.product_repo import ProductRepository

    async def scenario():
        engine, factory, _ = await _setup(tmp_path, monkeypatch)
        products = ProductRepository(factory)
        monkeypatch.setattr(policy_service, "product_repository", products)
        await products.upsert_products(
            [
                {"id": "tgdd-1", "name": "iPhone 16 128GB", "platform": "tgdd", "currentPrice": 19_990_000},
                {"id": "dmx-1", "name": "Điện thoại iPhone 16 256GB", "platform": "dmx", "currentPrice": 22_990_000},
                {
                    "id": "tiki-1",
                    "name": "Ốp lưng silicon trong suốt chống sốc cho iPhone 16",
                    "platform": "tiki",
                    "currentPrice": 59_000,
                },
                {
                    "id": "tgdd-2",
                    "name": "Điện thoại Samsung Galaxy S26 FE",
                    "platform": "tgdd",
                    "currentPrice": 12_990_000,
                },
            ]
        )
        all_ids = ["tiki", "tgdd", "dmx", "fpt-shop", "cellphones"]
        return {
            "catalog": await policy_service.resolve_scope("iPhone 16 bị lỗi màn hình có đổi được không", all_ids),
            "selected": await policy_service.resolve_scope("iPhone 16", ["dmx", "tiki"]),
            "model": await policy_service.resolve_scope("Samsung Galaxy S25 trả lại mất phí không", all_ids),
            "link": await policy_service.resolve_scope("https://fptshop.com.vn/dien-thoai/iphone-16 lỗi", all_ids),
            "bad_link": await policy_service.resolve_scope("https://shop.example.com/sp/1", all_ids),
            "product": await policy_service.resolve_scope("so sánh", all_ids, ["tgdd", "tgdd", "dmx"]),
        }, await engine.dispose()

    s, _ = asyncio.run(scenario())
    assert s["catalog"]["kind"] == "catalog" and s["catalog"]["platformIds"] == [
        "tgdd",
        "dmx",
    ]  # ốp lưng Tiki không tính
    assert s["selected"]["platformIds"] == ["dmx"]
    assert s["model"]["kind"] == "compare"  # không có S25 -> không nới sang S26
    assert s["link"] == {"kind": "link", "platformIds": ["fpt-shop"], "matches": {}}
    assert s["bad_link"]["kind"] == "unknown_link" and s["bad_link"]["platformIds"] == []
    assert s["product"]["platformIds"] == ["tgdd", "dmx"]


def test_parse_answer_keeps_only_known_sources():
    answer, ids = policy_service.parse_answer(
        '```json\n{"answer": "Được trả, phí 20% tháng đầu.", "source_ids": [5, "7", 99, 5]}\n```', [5, 7, 8]
    )
    assert answer == "Được trả, phí 20% tháng đầu." and ids == [5, 7]
    assert policy_service.parse_answer("Câu trả lời thường, không phải JSON", [1]) == (
        "Câu trả lời thường, không phải JSON",
        [],
    )


def test_scenario_steers_prompt_and_excerpts(tmp_path, monkeypatch):
    llm = _FakeLLM('{"answer": "Đổi ý vẫn trả được nhưng mất phí.", "source_ids": []}')
    monkeypatch.setattr(policy_service, "get_chat_model", lambda temperature=0.0, fast=False: llm)

    async def scenario():
        engine, _, repo = await _setup(tmp_path, monkeypatch)
        await policy_service.ensure_seeded()
        url = "https://www.thegioididong.com/chinh-sach-bao-hanh-san-pham"
        await repo.upsert_document(
            "tgdd",
            "return",
            "Chính sách",
            url,
            [
                "Bảo hành tại cửa hàng trong 12 tháng.",
                "Hoàn tiền: áp dụng cho sản phẩm lỗi và không lỗi, tháng đầu phí 20% giá trị hóa đơn.",
            ],
        )
        result = await policy_service.lookup("iPhone 16", ["tgdd"], scenario="change_mind")
        prompt = llm.prompt
        unknown = await policy_service.lookup("iPhone 16", ["tgdd"], scenario="khong-co")
        await engine.dispose()
        return result, prompt, unknown

    result, prompt, unknown = asyncio.run(scenario())
    assert result["scenario"] == "change_mind" and result["summary"] == "Đổi ý vẫn trả được nhưng mất phí."
    assert "ĐỔI Ý" in prompt  # hướng câu trả lời theo tình huống
    assert "20%" in result["excerpts"][0]["text"]  # đoạn về phí trả hàng không lỗi được xếp đầu
    assert unknown["scenario"] is None
