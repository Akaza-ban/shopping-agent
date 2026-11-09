"""
Kiểm thử RAG sản phẩm: embedding qua API (giả lập offline), BM25 + RRF, chuẩn hóa danh mục,
độ mới, dự phòng khi embedding API lỗi, và bộ đánh giá recall@k / MRR.

Test đánh giá trên kho thật (bge-m3 qua OpenRouter) chỉ chạy khi đặt RUN_LIVE_TESTS=1.
"""

import hashlib
import math
import os
import re
import time

import pytest

from integrations.embedding import EmbeddingError
from services.catalog.categories import categorize
from services.rag import ProductRAGService
from services.rag.evaluation import evaluate, evaluate_service, load_eval_set
from shared.categories import canonical_code, tiki_path_from_breadcrumbs


class FakeEmbeddings:
    """Embedding giả: băm từ vào 256 chiều (cùng từ -> cùng hướng), đủ để kiểm thử luồng xử lý."""

    model = "fake-hash"

    def __init__(self):
        self.fail = False
        self.calls = 0

    @property
    def available(self):
        return not self.fail

    def _vec(self, text):
        v = [0.0] * 256
        for w in re.findall(r"\w+", text.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts):
        self.calls += 1
        if self.fail:
            raise EmbeddingError("API lỗi (giả lập)")
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def _product(pid, name, price, category="all", platform="tiki", url="", specs=None, rating=4.5, path=None):
    return {
        "id": pid,
        "name": name,
        "category": category,
        "categoryName": "",
        "platform": platform,
        "platformName": platform.upper(),
        "currentPrice": price,
        "originalPrice": price,
        "discountPercent": 0,
        "rating": rating,
        "externalUrl": url or f"https://example.vn/{pid}",
        "specs": specs or {},
        "sourceCategoryPath": path,
    }


CATALOG = [
    _product(
        "p1",
        "Laptop Lenovo Gaming LOQ 15ARP10",
        30_000_000,
        "laptop",
        specs={"Card màn hình": "NVIDIA GeForce RTX 3050 6GB"},
        path="1/2/1846/8095",
    ),
    _product("p2", "Laptop HP 15 fc0023AU R5 7520U", 22_000_000, "laptops", path="1/2/1846/8095"),
    _product("p3", "Balo Laptop Xbags Modern", 369_000, "laptop", path="1/2/6000/27608"),
    _product(
        "p4",
        "Máy giặt LG Inverter 9 kg FB1209S5W",
        9_290_000,
        "all",
        "dmx",
        url="https://www.dienmayxanh.com/may-giat/lg-fb1209s5w",
    ),
    _product("p5", "Tai nghe chụp tai Sony WH-1000XM5", 7_599_000, "audio", path="1/2/1815/8215"),
    _product("p6", "Chảo chống dính Elmich EL4718OL", 205_000, "all", path="1/2/1951"),
    _product("p7", "Sản phẩm Shopee tai nghe", 130_000, "all", "shopee"),
]


@pytest.fixture
def rag(tmp_path):
    svc = ProductRAGService(
        persist_directory=str(tmp_path / "chroma"),
        collection_name="test_products",
        embedder=FakeEmbeddings(),
        max_age_days=30,
        disabled_platforms=["shopee"],
    )
    assert svc.upsert_products(CATALOG) == len(CATALOG)
    return svc


# ---------------------------------------------------------------- chuẩn hóa danh mục


def test_categorize_uses_learned_mappings(_offline_category_resolver):
    """Ngành hàng lấy từ bảng quy đổi danh mục của sàn; danh mục chưa quy đổi -> "other", không đoán từ tên."""
    _offline_category_resolver.remember(
        {
            "tiki:1/2/1846/8095": ("laptops", False),
            "tiki:1/2/6000/27608": ("other", True),
            "dmx:may-giat": ("home_appliances", False),
            "tgdd:dtdd": ("phones", False),
        }
    )
    assert (
        categorize({"platform": "tiki", "name": "Laptop Asus Vivobook", "sourceCategoryPath": "1/2/1846/8095"})
        == "laptops"
    )
    assert categorize({"platform": "tiki", "name": "Balo Laptop", "sourceCategoryPath": "1/2/6000/27608"}) == "other"
    assert (
        categorize({"name": "Panasonic Inverter 10 Kg", "externalUrl": "https://www.dienmayxanh.com/may-giat/na-fj100"})
        == "home_appliances"
    )
    assert categorize({"name": "iPhone 15", "externalUrl": "https://www.thegioididong.com/dtdd/iphone-15"}) == "phones"
    # Chưa quy đổi / không có danh mục của sàn -> "other" (kể cả khi tên hay nhãn cũ gợi ý ngành hàng)
    assert categorize({"category": "laptops", "name": "Laptop Asus Vivobook"}) == "other"
    assert (
        categorize({"name": "Điện thoại iPhone 15", "externalUrl": "https://www.thegioididong.com/slug-moi/x"})
        == "other"
    )
    assert categorize({"platform": "tiki", "name": "Thứ gì đó", "sourceCategoryPath": "1/2/99999"}) == "other"


def test_tiki_path_from_breadcrumbs_skips_product_entry():
    crumbs = [
        {"category_id": 1815, "name": "Thiết Bị Số"},
        {"category_id": 8215, "name": "Tai nghe"},
        {"category_id": 0, "name": "Tai nghe V9"},
    ]
    assert tiki_path_from_breadcrumbs(crumbs) == "1815/8215"


def test_data_processor_keeps_source_category():
    from services.catalog.data_processor import data_processor

    out = data_processor.process_product(
        {
            "id": "tiki-1",
            "name": "Tai nghe bluetooth V9",
            "platform": "tiki",
            "currentPrice": 150000,
            "externalUrl": "https://tiki.vn/tai-nghe-v9-p1.html",
            "sourceCategoryPath": "1/2/1815/8215",
            "sourceCategoryName": "Tai Nghe Bluetooth",
        }
    )
    assert out["sourceCategoryPath"] == "1/2/1815/8215"


def test_canonical_code_for_filters():
    assert canonical_code("laptop") == "laptops"
    assert canonical_code("phones") == "phones"
    assert canonical_code("all") == "all"
    assert canonical_code("không-có") is None


def test_search_filters_where_and_matcher_agree():
    from services.rag.filters import SearchFilters

    f = SearchFilters(category="laptop", max_price=25_000_000, excluded_platforms=["shopee"])
    assert f.where() == {
        "$and": [
            {"category": {"$eq": "laptops"}},
            {"platform": {"$nin": ["shopee"]}},
            {"current_price": {"$lte": 25_000_000.0}},
        ]
    }
    match = f.matcher()
    assert match({"category": "laptops", "platform": "tiki", "current_price": 22_000_000})
    assert not match({"category": "laptops", "platform": "shopee", "current_price": 22_000_000})
    assert not match({"category": "other", "platform": "tiki", "current_price": 300_000})
    assert SearchFilters(category="all").where() is None


# ---------------------------------------------------------------- nạp kho


def test_document_text_has_no_volatile_fields(rag):
    data = rag._collection.get(ids=["p5"], include=["documents", "metadatas"])
    doc, meta = data["documents"][0], data["metadatas"][0]
    assert "WH-1000XM5" in doc
    for volatile in ("7,599,000", "7599000", "VNĐ", "sao", "4.5"):
        assert volatile not in doc
    # giá, đánh giá, thời điểm vẫn ở metadata để lọc
    assert meta["current_price"] == 7_599_000 and meta["rating"] == 4.5 and meta["updated_at"] > 0


def test_upsert_stores_normalized_category(rag):
    metas = {m["product_id"]: m for m in rag.corpus()}
    assert metas["p1"]["category"] == "laptops"
    assert metas["p3"]["category"] == "other"
    assert metas["p4"]["category"] == "home_appliances"


def test_upsert_skips_when_embedding_api_down(tmp_path):
    emb = FakeEmbeddings()
    emb.fail = True
    svc = ProductRAGService(persist_directory=str(tmp_path / "c"), collection_name="t", embedder=emb)
    assert svc.upsert_products(CATALOG[:2]) == 0
    assert svc.count() == 0


# ---------------------------------------------------------------- truy xuất


def test_category_filter_excludes_mislabeled_accessories(rag):
    names = [p["name"] for p in rag.search("laptop", category="laptop", limit=5)]
    assert "Balo Laptop Xbags Modern" not in names
    assert any("Lenovo" in n for n in names)


def test_bm25_matches_model_code_in_specs(rag):
    cands = rag.retrieve_candidates("laptop RTX 3050", category="laptops")
    assert cands[0].id == "p1"
    assert cands[0].coverage == 1.0


def test_query_without_accents_matches(rag):
    cands = rag.retrieve_candidates("may giat inverter")
    assert cands and cands[0].id == "p4"


def test_price_filter(rag):
    results = rag.search("laptop", category="laptops", max_price=25_000_000, limit=5)
    assert [p["id"] for p in results] == ["p2"]


def test_disabled_platform_excluded(rag):
    ids = [c.id for c in rag.retrieve_candidates("tai nghe")]
    assert "p7" not in ids and "p5" in ids


def test_stale_products_skipped_and_pruned(rag):
    old = int(time.time()) - 40 * 86400
    rag.upsert_products([_product("old", "Tai nghe Sony WH-CH730N", 2_990_000, "audio")], timestamps=[old])
    assert "old" not in [c.id for c in rag.retrieve_candidates("tai nghe sony")]
    assert "old" in [c.id for c in rag.retrieve_candidates("tai nghe sony", max_age_days=None)]
    removed = rag.prune()
    assert removed == 2  # bản quá cũ + bản Shopee (sàn đang tắt)
    assert rag.count() == len(CATALOG) - 1


def test_search_returns_iso_updated_at_and_match_score(rag):
    p = rag.search("Tai nghe chụp tai Sony WH-1000XM5", limit=1)[0]
    assert p["id"] == "p5"
    assert 60 <= p["aiMatchScore"] <= 99
    assert p["updatedAt"].startswith("20")


def test_fallback_to_keyword_search_when_embedding_down(rag):
    rag.embedder.fail = True
    results = rag.search("Sony WH-1000XM5", limit=3)
    assert [p["id"] for p in results] == ["p5"]
    assert rag.retrieve_candidates("Sony WH-1000XM5")[0].distance is None
    # truy vấn chỉ khớp lỏng -> trả rỗng để hệ thống cào trực tiếp
    assert rag.search("tai nghe chống ồn giá rẻ cho sinh viên", limit=3) == []


def test_unrelated_query_returns_nothing(rag):
    assert rag.search("son môi màu đỏ", limit=3) == []


# ---------------------------------------------------------------- bộ đánh giá


def test_eval_metrics_on_toy_search():
    queries = [q for q in load_eval_set() if q["query"] in ("airpods", "son môi")]
    corpus = [
        {"name": "Tai nghe Bluetooth Apple AirPods 4", "external_url": "u1", "current_price": 2_890_000},
        {"name": "Chảo chống dính", "external_url": "u2", "current_price": 200_000},
    ]
    results = {
        "airpods": [
            {"name": "Chảo chống dính", "externalUrl": "u2"},
            {"name": "Tai nghe Bluetooth Apple AirPods 4", "externalUrl": "u1"},
        ],
        "son môi": [],
    }
    s = evaluate(lambda q: results[q["query"]], corpus, queries)["summary"]
    assert s["hit@1"] == 0.0 and s["hit@5"] == 1.0
    assert s["recall@5"] == 1.0 and s["mrr@10"] == 0.5 and s["precision@5"] == 0.5
    assert s["negative_reject_rate"] == 1.0


def test_eval_set_is_well_formed():
    queries = load_eval_set()
    positives = [q for q in queries if not q.get("negative")]
    assert len(positives) >= 40 and len(queries) - len(positives) >= 5
    for q in positives:
        assert q["_name"] or q["_url"], q["query"]


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_TESTS"), reason="Đặt RUN_LIVE_TESTS=1 để đo trên kho thật (gọi embedding API)"
)
def test_live_retrieval_quality():
    from services.rag import rag_service

    if rag_service.count() == 0:
        pytest.skip("Kho products_v2 rỗng — chạy python -m scripts.rag.reindex trước")
    report = evaluate_service(rag_service)
    s = report["summary"]
    # Mốc cũ (all-MiniLM-L6-v2, products_v1): recall@5 0.28, MRR 0.46
    assert s["recall@5"] >= 0.8, s
    assert s["mrr@10"] >= 0.8, s
    assert s["negative_reject_rate"] >= 0.6, s
