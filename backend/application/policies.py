"""Tra cứu chính sách đổi trả, bảo hành: lấy điều khoản từ CSDL, tìm đoạn trích liên quan, LLM tóm tắt dựa trên dữ liệu đó."""

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from database.repositories import policy_repository, product_repository
from integrations.llm import ask_llm, get_chat_model
from integrations.platforms import platform_for_url
from services.policy.seed import LAST_CHECKED, POLICY_SEED, document_text
from services.rag.bm25 import BM25Index
from services.rag.text import STOP_WORDS, query_terms, words
from shared.exceptions import LLMError

logger = logging.getLogger(__name__)

SUMMARY_TIMEOUT_SECONDS = 12.0
POLICY_TERMS = ["đổi", "trả", "bảo", "hành", "hoàn", "tiền", "lỗi"]
# Từ trong câu hỏi về đổi trả, không thuộc tên sản phẩm
POLICY_WORDS = set(POLICY_TERMS) | {
    "phí",
    "bao",
    "nhiêu",
    "muốn",
    "không",
    "thích",
    "ưng",
    "được",
    "bị",
    "mất",
    "lại",
    "vì",
    "trong",
    "tháng",
    "ngày",
    "sách",
    "sau",
    "khi",
    "nếu",
    "thì",
    "đã",
    "chưa",
    "mua",
    "về",
    "ra",
    "sao",
    "thế",
    "như",
    "gì",
    "hỏng",
    "hư",
    "vỡ",
    "rơi",
    "lâu",
    "của",
    "này",
    "đó",
    "ở",
    "nhận",
    "giao",
    "hàng",
    "kiểm",
    "tra",
    "cứu",
}
HEAD_CHARS = 15

SUMMARY_PROMPT = """Bạn trả lời câu hỏi về chính sách đổi trả, bảo hành của nơi bán sản phẩm.
Chỉ dùng dữ liệu được cung cấp, không thêm con số hay điều khoản nào khác. Mỗi điều khoản chỉ gán cho đúng nền tảng của nó.
Chỉ có một nền tảng: trả lời theo chính sách của nền tảng đó, không so sánh với nơi khác.
Nhiều nền tảng (cùng bán sản phẩm, hoặc người mua đang cân nhắc nơi mua): nêu cụ thể mức phí hoặc số ngày của từng nền tảng khi có.
Viết 2-4 câu trả lời đúng câu hỏi của người mua.
Ngoại lệ (exceptions) mâu thuẫn với kết luận thì phải nêu ra, không bỏ qua.
Nền tảng có verified=false là dữ liệu chưa đối chiếu với trang chính sách gốc: nếu nhắc tới thì nói rõ cần kiểm tra lại.
Câu đầu tiên là kết luận ngắn (được/không được, mất phí gì). Không dùng markdown, không mở đầu bằng lời chào.
Trả về đúng một JSON, không markdown: {"answer": "câu trả lời", "source_ids": [id các đoạn trích làm căn cứ]}"""

SCENARIOS = {
    "defect": (
        "Người mua hỏi về sản phẩm bị LỖI DO NHÀ SẢN XUẤT: có được đổi / trả / bảo hành không, trong bao lâu, "
        "mất phí gì.",
        ["lỗi", "nhà", "sản", "xuất", "đổi", "kỹ", "thuật"],
    ),
    "change_mind": (
        "Người mua ĐỔI Ý, sản phẩm KHÔNG LỖI: có trả được không, mất phí bao nhiêu và phí thay đổi theo "
        "thời gian ra sao.",
        ["không", "lỗi", "nhu", "cầu", "phí", "khấu", "hao", "hoàn", "tiền", "trả"],
    ),
    "wrong_item": (
        "Người mua nhận hàng GIAO SAI, THIẾU hoặc HƯ HỎNG KHI VẬN CHUYỂN: xử lý thế nào, cần làm gì khi nhận hàng.",
        ["giao", "sai", "thiếu", "vận", "chuyển", "nhận", "kiểm", "tra", "hủy"],
    ),
    "warranty": (
        "Người mua hỏi về BẢO HÀNH: ai tiếp nhận, ở đâu, thời hạn bao lâu, điều kiện được bảo hành.",
        ["bảo", "hành", "hãng", "trung", "tâm", "tiếp", "nhận", "sửa"],
    ),
}


async def ensure_seeded() -> None:
    """Nạp chính sách mẫu khi kho chính sách còn trống (lần chạy đầu)."""
    if not await policy_repository.is_empty():
        return
    for item in POLICY_SEED:
        await policy_repository.upsert_platform_policy(
            item, item["terms"], document_text(item["name"], item["terms"]), last_checked=LAST_CHECKED
        )
    logger.info("Đã nạp chính sách cho %d nền tảng", len(POLICY_SEED))


async def find_excerpts(
    query: str, platform_ids: list[str], per_platform: int = 2, extra_terms: list[str] | None = None
) -> list[dict[str, Any]]:
    """Các đoạn liên quan nhất của từng nền tảng (trang dài như TGDĐ không lấn hết chỗ của nền tảng khác)."""
    chunks = await policy_repository.list_chunks(platform_ids)
    if not chunks:
        return []
    index = BM25Index([str(c["id"]) for c in chunks], [c["text"] for c in chunks], chunks)
    terms = words(" ".join((extra_terms or []) + (query_terms(query) if query else []) + POLICY_TERMS))
    by_id = {str(c["id"]): c for c in chunks}
    out: list[dict[str, Any]] = []
    for pid in platform_ids:
        ids = index.top(terms, per_platform, keep=lambda m, pid=pid: m["platformId"] == pid)
        out += [by_id[i] for i in ids]
    return out


def fallback_summary(query: str, policies: list[dict[str, Any]], language: str) -> str:
    if len(policies) == 1:
        p = policies[0]
        if language == "en":
            return (
                f"{p['platformName']}: returns within {p['returnWindowDays']} days; "
                f"see the conditions and exceptions below."
            )
        return (
            f"{p['platformName']}: đổi trả trong {p['returnWindowDays']} ngày. {p['defectExchange']}. "
            f"Xem điều kiện và ngoại lệ bên dưới."
        )
    best = max(policies, key=lambda p: (p["returnWindowDays"], p["freeReturn"]))
    if language == "en":
        free = ", free returns" if best["freeReturn"] else ""
        return (
            f'For "{query}", {best["platformName"]} has the longest return window '
            f"({best['returnWindowDays']} days{free}). Check exceptions before buying."
        )
    free = ", miễn phí trả hàng" if best["freeReturn"] else ""
    return (
        f'Với "{query}", {best["platformName"]} có thời hạn đổi trả dài nhất '
        f"({best['returnWindowDays']} ngày{free}). Hãy xem phần ngoại lệ trước khi mua."
    )


def _valid_source_ids(raw_ids: Any, excerpt_ids: list[int]) -> list[int]:
    """Các id LLM trích dẫn có thật trong danh sách đoạn trích (bỏ trùng, bỏ giá trị không phải số)."""
    ids: list[int] = []
    for value in raw_ids or []:
        try:
            source_id = int(value)
        except (TypeError, ValueError):
            continue
        if source_id in excerpt_ids and source_id not in ids:
            ids.append(source_id)
    return ids


def parse_answer(raw: str, excerpt_ids: list[int]) -> tuple[str, list[int]]:
    """JSON {"answer", "source_ids"} của LLM -> (câu trả lời, id đoạn trích hợp lệ); không phải JSON thì giữ nguyên chữ."""
    text = (raw or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict) or not str(data.get("answer") or "").strip():
        return text, []
    return str(data["answer"]).strip(), _valid_source_ids(data.get("source_ids"), excerpt_ids)


async def summarize(
    query: str,
    policies: list[dict[str, Any]],
    excerpts: list[dict[str, Any]],
    language: str,
    scenario: str | None = None,
) -> tuple:
    """(câu trả lời, id đoạn trích làm căn cứ, có dùng LLM không)."""
    model = get_chat_model(temperature=0.0)
    if model is None:
        return fallback_summary(query, policies, language), [], False
    data = {
        "cau_hoi": query,
        "tinh_huong": SCENARIOS[scenario][0] if scenario in SCENARIOS else "",
        "chinh_sach": [
            {
                k: p[k]
                for k in (
                    "platformName",
                    "returnWindowDays",
                    "freeReturn",
                    "returnConditions",
                    "returnShippingFee",
                    "refundTime",
                    "defectExchange",
                    "warrantyHandling",
                    "exceptions",
                    "verified",
                )
            }
            for p in policies
        ],
        "doan_trich": [{"id": e["id"], "nen_tang": e["platformId"], "text": e["text"]} for e in excerpts],
    }
    lang = "Trả lời bằng tiếng Anh." if language == "en" else "Trả lời bằng tiếng Việt."
    try:
        raw = await ask_llm(
            model,
            [
                SystemMessage(content=SUMMARY_PROMPT + "\n" + lang),
                HumanMessage(content=json.dumps(data, ensure_ascii=False, separators=(",", ":"))),
            ],
            timeout=SUMMARY_TIMEOUT_SECONDS,
        )
    except LLMError as e:
        logger.warning("LLM tóm tắt chính sách lỗi, dùng tóm tắt dựng sẵn: %s", e)
        return fallback_summary(query, policies, language), [], False
    answer, source_ids = parse_answer(raw, [e["id"] for e in excerpts])
    if answer:
        return answer, source_ids, True
    return fallback_summary(query, policies, language), [], False


def platform_from_url(text: str) -> str | None:
    m = re.search(r"https?://\S+", text or "")
    if not m:
        return None
    platform = platform_for_url(m.group(0))
    return platform.id if platform else None


def product_terms(query: str) -> list[str]:
    """Từ khóa chỉ tên sản phẩm: bỏ từ dừng và từ vựng về đổi trả ("iPhone 16 lỗi có đổi được không" -> iphone, 16)."""
    return [w for w in words(query) if w not in STOP_WORDS and w not in POLICY_WORDS]


async def find_selling_platforms(query: str) -> dict[str, list[dict[str, Any]]]:
    """{sàn: sản phẩm khớp tên} trong kho đã cào."""
    terms = product_terms(query)
    while terms:
        if len(terms) > 1 or len(terms[0]) >= 4 or any(c.isdigit() for c in terms[0]):
            found = [
                p
                for p in await product_repository.find_by_name_terms(terms)
                if 0 <= (p["name"] or "").lower().find(terms[0]) <= HEAD_CHARS
            ]
            if found:
                by_platform: dict[str, list[dict[str, Any]]] = {}
                for p in found:
                    by_platform.setdefault(p["platform"], []).append(p)
                return by_platform
        if any(c.isdigit() for c in terms[-1]):
            break
        terms = terms[:-1]
    return {}


async def resolve_scope(
    query: str, platform_ids: list[str], product_platform_ids: list[str] | None = None
) -> dict[str, Any]:
    """Nền tảng cần tra chính sách: sàn của sản phẩm đang xem / của link / nơi đang bán sản phẩm trong kho / các sàn người dùng chọn."""
    if product_platform_ids:
        return {"kind": "product", "platformIds": list(dict.fromkeys(product_platform_ids)), "matches": {}}
    pid = platform_from_url(query)
    if pid:
        return {"kind": "link", "platformIds": [pid], "matches": {}}
    if re.search(r"https?://", query or ""):
        return {"kind": "unknown_link", "platformIds": [], "matches": {}}
    selling = await find_selling_platforms(query)
    if selling:
        ids = [p for p in platform_ids if p in selling] or list(selling)
        matches = {p: {"count": len(selling[p]), "example": selling[p][0]["name"]} for p in ids}
        return {"kind": "catalog", "platformIds": ids, "matches": matches}
    return {"kind": "compare", "platformIds": platform_ids, "matches": {}}


async def list_policies(platform_ids: list[str] | None, category: str = "all") -> list[dict[str, Any]]:
    """Điều khoản đổi trả, bảo hành của các nền tảng (None = tất cả)."""
    return await policy_repository.list_policies(platform_ids, category)


async def lookup(
    query: str,
    platform_ids: list[str],
    category: str = "all",
    language: str = "vi",
    product_platform_ids: list[str] | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    scope = await resolve_scope(query, platform_ids, product_platform_ids)
    scenario = scenario if scenario in SCENARIOS else None
    result = {
        "policies": [],
        "excerpts": [],
        "summary": "",
        "sourceIds": [],
        "usedLlm": False,
        "scope": scope,
        "scenario": scenario,
    }
    policies = await policy_repository.list_policies(scope["platformIds"], category) if scope["platformIds"] else []
    if not policies:
        return result
    ids = [p["platformId"] for p in policies]
    excerpts = await find_excerpts(
        query, ids, per_platform=3 if len(ids) == 1 else 2, extra_terms=SCENARIOS[scenario][1] if scenario else None
    )
    summary, source_ids, used_llm = await summarize(query, policies, excerpts, language, scenario)
    result.update(policies=policies, excerpts=excerpts, summary=summary, sourceIds=source_ids, usedLlm=used_llm)
    return result
