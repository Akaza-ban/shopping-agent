"""Chấm mức hợp nhu cầu từ thông số trên trang (spec_fit.py) thay cho dò từ khóa trong tên (chạy offline, LLM giả)."""

import asyncio
import json
from types import SimpleNamespace

from core.state import UniversalSearchCriteria
from services.catalog import spec_fit
from services.catalog.ranker import check_attribute, rank_products, score_product


def _laptop(pid, specs, name=None, price=20_000_000, detail=True):
    return {
        "id": pid,
        "name": name or f"Laptop {pid}",
        "currentPrice": price,
        "originalPrice": price,
        "rating": 4.6,
        "reviewsCount": "120 đánh giá",
        "specs": specs,
        "detailFetched": detail,
    }


class FakeModel:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    async def ainvoke(self, messages):
        self.prompts.append(messages[1].content)
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(content=json.dumps(self.reply, ensure_ascii=False))


def _use(monkeypatch, model):
    spec_fit._cache.clear()
    monkeypatch.setattr(spec_fit, "get_chat_model", lambda **_: model)


GAMING = UniversalSearchCriteria(category="laptops", usage_purpose="chơi game", max_price=25_000_000)


# ---------------------------------------------------------------- xếp hạng dùng điểm từ thông số
def test_spec_fit_decides_ranking_without_keywords_in_name():
    # Máy gaming không có chữ "Gaming" trong tên vẫn đứng đầu nhờ thông số
    strong = {**_laptop("legion", {"GPU": "RTX 4060"}), "specFit": {"score": 0.9, "reason": "RTX 4060 chơi game tốt"}}
    weak = {
        **_laptop("office", {"GPU": "Intel UHD"}, name="Laptop Gaming Văn Phòng"),
        "specFit": {"score": 0.2, "reason": "GPU tích hợp, không chơi game nặng"},
    }
    ranked, _ = rank_products([weak, strong], GAMING)
    assert [p["id"] for p in ranked] == ["legion", "office"]
    assert any(r.startswith("Hợp nhu cầu theo thông số") for r in ranked[0]["matchReasons"])
    assert any(r.startswith("Không hợp nhu cầu theo thông số") for r in ranked[1]["matchReasons"])


def test_without_spec_fit_component_is_skipped():
    score_without, reasons, _ = score_product(_laptop("a", {}), GAMING)
    assert not any("nhu cầu" in r for r in reasons)
    assert 0 < score_without <= 100


def test_brand_preference_only_counts_when_user_mentions_brands():
    c = UniversalSearchCriteria(brands=["Lenovo"])
    lenovo = score_product(_laptop("a", {}, name="Laptop Lenovo LOQ"), c)
    other = score_product(_laptop("b", {}, name="Laptop Acer Nitro"), c)
    assert lenovo[0] > other[0] and "Đúng hãng bạn chọn" in lenovo[1]


def test_mismatch_from_spec_fit_needs_detail_page():
    p = {**_laptop("a", {"Ổ cứng": "512 GB SSD"}), "specMismatch": {"ssd": "512 GB SSD"}}
    assert check_attribute(p, "ssd", "1TB") == ("mismatch", "512 GB SSD")
    assert check_attribute({**p, "detailFetched": False}, "ssd", "1TB") == ("unknown", None)


# ---------------------------------------------------------------- bước chấm bằng LLM
def test_assess_scores_only_products_with_specs(monkeypatch):
    model = FakeModel(
        {
            "products": [
                {"id": "a", "fit": 9, "reason": "RTX 4060, RAM 16GB", "mismatch": {}},
                {"id": "b", "fit": 14, "reason": "quá điểm", "mismatch": {}},
            ]
        }
    )
    _use(monkeypatch, model)
    products = [_laptop("a", {"GPU": "RTX 4060"}), _laptop("b", {"GPU": "RTX 4050"}), _laptop("c", {})]
    out = asyncio.run(spec_fit.assess(products, GAMING))
    by_id = {p["id"]: p for p in out}
    assert by_id["a"]["specFit"] == {"score": 0.9, "reason": "RTX 4060, RAM 16GB"}
    assert by_id["b"]["specFit"]["score"] == 1.0  # chặn trong 0..1
    assert "specFit" not in by_id["c"]  # không có thông số thì không chấm
    assert '"id":"c"' not in model.prompts[0]
    assert "chơi game" in model.prompts[0]
    assert "specFit" not in products[0]  # không sửa danh sách gốc


def test_assess_rejects_mismatch_value_not_on_page(monkeypatch):
    _use(
        monkeypatch,
        FakeModel(
            {
                "products": [
                    {"id": "a", "fit": 5, "reason": "", "mismatch": {"ssd": "512 GB SSD"}},
                    {"id": "b", "fit": 5, "reason": "", "mismatch": {"ssd": "256 GB"}},  # bịa: trang không ghi
                ]
            }
        ),
    )
    products = [_laptop("a", {"Ổ cứng": "512 GB SSD"}), _laptop("b", {"Ổ cứng": "1 TB SSD"})]
    out = asyncio.run(spec_fit.assess(products, GAMING, {"ssd": "1TB"}))
    assert out[0]["specMismatch"] == {"ssd": "512 GB SSD"}
    assert "specMismatch" not in out[1]


def test_assess_survives_llm_error(monkeypatch):
    from shared.exceptions import LLMError

    _use(monkeypatch, FakeModel(LLMError("hết hạn mức")))
    out = asyncio.run(spec_fit.assess([_laptop("a", {"GPU": "RTX 4060"})], GAMING))
    assert "specFit" not in out[0]


def test_assess_reuses_cached_scores(monkeypatch):
    model = FakeModel({"products": [{"id": "a", "fit": 8, "reason": "ok", "mismatch": {}}]})
    _use(monkeypatch, model)
    products = [_laptop("a", {"GPU": "RTX 4060"})]
    asyncio.run(spec_fit.assess(products, GAMING))
    again = asyncio.run(spec_fit.assess(products, GAMING))
    assert again[0]["specFit"]["score"] == 0.8 and len(model.prompts) == 1
