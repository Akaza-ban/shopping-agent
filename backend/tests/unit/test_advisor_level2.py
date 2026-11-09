"""
Kiểm thử Mức 2 của luồng tư vấn mua sắm (chạy offline, không gọi mạng/LLM):
- Đọc thông số & bảo hành/đổi trả từ trang chi tiết (TGDĐ fixture thật, Tiki JSON).
- Xếp hạng theo tiêu chí: đúng/sai/chưa rõ thông số, ngân sách, rating có trọng số lượt đánh giá.
- Bảng so sánh có cấu trúc.
- Hỏi làm rõ ngân sách & gộp câu trả lời vào tiêu chí.
"""

import os
from datetime import UTC, datetime, timedelta

from core.flows import clarification
from core.state import AgentState, UniversalSearchCriteria
from core.tools import attribute_match
from core.tools.ecom_search import EcomSearchTool
from core.tools.spec_comparator import SpecComparatorTool
from integrations.platforms.common import canonical_spec_label
from integrations.platforms.mwg import parse_mwg_detail
from integrations.platforms.tiki import parse_tiki_detail
from services.catalog.enricher import ProductEnricher
from services.catalog.ranker import parse_volume, rank_products, score_product, verifiable_attributes

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _laptop(pid, price, gpu=None, rating=4.8, reviews="Đã bán 2,4k", detail=True, name=None):
    specs = {"RAM": "16 GB"}
    if gpu:
        specs["GPU"] = gpu
    return {
        "id": pid,
        "name": name or f"Laptop {pid}",
        "platform": "tgdd",
        "platformName": "Thế Giới Di Động",
        "currentPrice": price,
        "originalPrice": price,
        "discountPercent": 0,
        "rating": rating,
        "reviewsCount": reviews,
        "specs": specs,
        "detailFetched": detail,
    }


# ---------------------------------------------------------------- trang chi tiết
def test_parse_mwg_detail_fixture():
    with open(os.path.join(FIXTURES, "tgdd_laptop_detail_2026.html"), encoding="utf-8") as f:
        detail = parse_mwg_detail(f.read())
    assert "RTX 3050" in detail["specs"]["GPU"]
    assert "13420H" in detail["specs"]["CPU"]
    assert detail["specs"]["RAM"].startswith("16 GB")
    assert detail["warranty"].startswith("Bảo hành chính hãng Laptop 1 năm")
    assert detail["returnPolicy"].startswith("Hư gì đổi nấy 12 tháng tại 2.984 siêu thị")


def test_parse_tiki_detail():
    data = {
        "specifications": [
            {
                "name": "Content",
                "attributes": [
                    {"name": "Card đồ họa", "value": "NVIDIA RTX 4060"},
                    {"name": "Thời gian bảo hành", "value": "24 tháng"},
                ],
            }
        ],
        "return_and_exchange_policy": "Đổi trả trong<br><b>7 ngày</b><br>nếu sp lỗi.",
    }
    detail = parse_tiki_detail(data)
    assert detail["specs"]["GPU"] == "NVIDIA RTX 4060"
    assert detail["warranty"] == "Thời gian bảo hành: 24 tháng"
    assert detail["returnPolicy"] == "Đổi trả trong 7 ngày nếu sp lỗi."


def test_canonical_labels_specific_before_generic():
    assert canonical_spec_label("Khối lượng giặt:") == "Khối lượng giặt"
    assert canonical_spec_label("Kích thước, khối lượng:") == "Khối lượng"
    assert canonical_spec_label("Chip đồ họa (GPU):") == "GPU"


def test_merge_detail_overrides_listing_specs():
    merged = ProductEnricher.merge_detail(
        {"specs": {"RAM": "RAM 16 GB"}, "warranty": "Chính hãng TGDĐ"},
        {
            "specs": {"RAM": "16 GB", "GPU": "RTX 3050"},
            "warranty": "Bảo hành chính hãng 2 năm",
            "returnPolicy": "Hư gì đổi nấy 12 tháng",
        },
    )
    assert merged["specs"] == {"RAM": "16 GB", "GPU": "RTX 3050"}
    assert merged["warranty"] == "Bảo hành chính hãng 2 năm"
    assert merged["returnPolicy"] == "Hư gì đổi nấy 12 tháng"
    assert merged["detailFetched"] is True


# ---------------------------------------------------------------- xếp hạng
def test_rank_verified_beats_unknown_beats_mismatch():
    c = UniversalSearchCriteria(max_price=30_000_000, attributes={"gpu": "RTX 4070"})
    products = [
        _laptop("mismatch", 25_000_000, gpu="NVIDIA GeForce RTX 3050"),
        _laptop("unknown", 25_000_000, detail=False),
        _laptop("verified", 29_000_000, gpu="NVIDIA GeForce RTX 4070 8GB"),
    ]
    ranked, notes = rank_products(products, c)
    assert [p["id"] for p in ranked] == ["verified", "unknown", "mismatch"]
    assert ranked[2]["attributeMatch"] == {"gpu": "mismatch"}
    assert any("RTX 3050" in r for r in ranked[2]["matchReasons"])
    assert notes and "KHÔNG đúng yêu cầu" in notes[0]


def test_rank_penalizes_over_budget():
    c = UniversalSearchCriteria(max_price=20_000_000)
    in_budget, over = score_product(_laptop("a", 19_000_000), c), score_product(_laptop("b", 24_000_000), c)
    assert in_budget[0] > over[0]
    assert any("Vượt ngân sách" in r for r in over[1])


def test_rating_weighted_by_volume():
    c = UniversalSearchCriteria()
    few = score_product(_laptop("few", 10_000_000, rating=5.0, reviews="2 đánh giá"), c)[0]
    many = score_product(_laptop("many", 10_000_000, rating=4.8, reviews="Đã bán 3,4k"), c)[0]
    assert many > few
    assert parse_volume("Đã bán 3,4k") == 3400 and parse_volume("Chưa có đánh giá") == 0


def test_verifiable_attributes_ignore_free_text():
    c = UniversalSearchCriteria(attributes={"gpu": "RTX 4070", "need": "phù hợp gia đình 4 người", "anc": True})
    assert verifiable_attributes(c) == {"gpu": "RTX 4070"}


# ---------------------------------------------------------------- so sánh
def test_comparison_table_marks_best_cells():
    products = [
        {
            **_laptop("a", 25_000_000, gpu="RTX 3050"),
            "aiMatchScore": 70,
            "warranty": "1 năm",
            "returnPolicy": "Hư gì đổi nấy 12 tháng",
        },
        {
            **_laptop("b", 22_000_000, gpu="RTX 3050", rating=4.2),
            "aiMatchScore": 60,
            "specs": {"RAM": "32 GB", "GPU": "RTX 3050"},
        },
    ]
    table = SpecComparatorTool().build_table(products)
    rows = {r["label"]: r for r in table["rows"]}
    assert rows["Giá hiện tại"]["best_index"] == 1
    assert rows["Điểm phù hợp"]["best_index"] == 0
    assert rows["RAM"]["best_index"] == 1
    assert rows["Đổi trả"]["values"] == ["Hư gì đổi nấy 12 tháng", "Theo chính sách của sàn"]
    md = SpecComparatorTool.table_to_markdown(table)
    assert md.startswith("| Tiêu chí |") and "**22,000,000 đ**" in md


# ---------------------------------------------------------------- làm rõ & tiện ích
def test_clarification_asked_once_and_answer_merged(monkeypatch):
    from memory.session_manager import session_memory

    monkeypatch.setattr(session_memory, "get_last_products", lambda sid: [])
    broad = UniversalSearchCriteria(
        category="laptops", product_type="laptop gaming", target_entity="laptop", cleaned_query="laptop gaming"
    )

    s1 = AgentState(session_id="clar-1", user_query="tìm laptop gaming", intent="search_products", criteria=broad)
    clarification.maybe_ask(s1)
    assert s1.clarification and s1.clarification["field"] == "budget"
    assert any("Không giới hạn" in o["label"] for o in s1.clarification["options"])

    # Lượt trả lời: router chỉ trích được ngân sách -> gộp vào tiêu chí đang chờ
    s2 = AgentState(
        session_id="clar-1",
        user_query="20 - 25 triệu",
        intent="general_advice",
        criteria=UniversalSearchCriteria(min_price=20_000_000, max_price=25_000_000),
    )
    clarification.apply_pending(s2)
    assert s2.intent == "search_products"
    assert s2.criteria.cleaned_query == "laptop gaming" and s2.criteria.max_price == 25_000_000

    # Không hỏi lại cùng ngành hàng trong phiên
    s3 = AgentState(session_id="clar-1", user_query="tìm laptop gaming khác", intent="search_products", criteria=broad)
    clarification.maybe_ask(s3)
    assert s3.clarification is None


def test_no_clarification_when_query_is_specific():
    for crit, q in [
        (
            UniversalSearchCriteria(category="phones", product_type="iPhone 15", target_entity="điện thoại"),
            "tìm iphone 15",
        ),
        (
            UniversalSearchCriteria(category="laptops", target_entity="laptop", max_price=20_000_000),
            "laptop dưới 20 triệu",
        ),
        (UniversalSearchCriteria(category="audio", target_entity="tai nghe", brands=["Sony"]), "tai nghe sony"),
    ]:
        s = AgentState(session_id=f"spec-{q}", user_query=q, intent="search_products", criteria=crit)
        clarification.maybe_ask(s)
        assert s.clarification is None, q


def test_crawler_query_drops_budget_phrases():
    tool = EcomSearchTool()
    c = UniversalSearchCriteria(cleaned_query="máy giặt 5-10 triệu cửa trước", target_entity="máy giặt")
    assert tool.optimize_crawler_query(c.cleaned_query, c) == "máy giặt cửa trước"
    c2 = UniversalSearchCriteria(cleaned_query="laptop gaming dưới 30tr", target_entity="laptop")
    assert tool.optimize_crawler_query(c2.cleaned_query, c2) == "laptop gaming"


def test_freshness_note():
    old = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    note = attribute_match.freshness_note([{"updatedAt": old}])
    assert note and "30 giờ" in note
    assert attribute_match.freshness_note([{"updatedAt": datetime.now(UTC).isoformat()}]) is None
