"""Chấm mức hợp nhu cầu của từng sản phẩm từ thông số đọc được trên trang (bằng LLM), thay cho dò từ khóa trong tên.

assess(products, criteria) trả về bản sao các sản phẩm, sản phẩm nào có thông số thì thêm:
    specFit        {"score": 0..1, "reason": "..."}           mức hợp nhu cầu + lý do trích từ thông số
    specMismatch   {khóa thông số: giá trị thực tế}              thông số yêu cầu mà trang ghi khác
Không có LLM / LLM lỗi / quá thời gian / sản phẩm không có thông số -> không thêm gì,
bộ xếp hạng bỏ qua thành phần này (lượt tư vấn không bao giờ hỏng vì bước chấm).
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from integrations.llm import ask_llm, get_chat_model, parse_llm_json
from shared.exceptions import LLMError

logger = logging.getLogger("spec_fit")

FIT_BUDGET_SECONDS = 8.0  # chờ tối đa cho một lượt chấm; quá thì xếp hạng không có thành phần này
MAX_PRODUCTS = 12
MAX_SPEC_ITEMS = 15
MAX_SPEC_VALUE_CHARS = 80
MAX_REASON_CHARS = 120
CACHE_TTL_SECONDS = 6 * 3600
CACHE_MAX_ENTRIES = 2000

PRIORITY_NEEDS = {
    "cheapest": "giá rẻ nhất, cấu hình chỉ cần đủ dùng",
    "best_performance": "hiệu năng mạnh nhất có thể",
    "best_rating": "bền, ổn định, ít lỗi",
    "brand_reputation": "thương hiệu uy tín, chất lượng hoàn thiện tốt",
    "best_value": "cấu hình đáng tiền nhất so với giá",
}

_FIT_RULES = """- Được dùng kiến thức chuyên môn để đánh giá linh kiện / công nghệ GHI TRONG bảng thông số (VD RTX 4060 đủ chơi game nặng ở 1080p, RAM 8GB hơi ít cho đồ họa).
- KHÔNG suy ra thông số không có trong bảng từ tên sản phẩm hay trí nhớ. Bảng trống hoặc thiếu thông tin quyết định cho nhu cầu -> "fit": null.
- "fit": số nguyên 0-10 (10 = rất hợp nhu cầu). Nhu cầu có yếu tố giá ("đáng tiền", "giá rẻ") thì xét cả giá.
- "reason": tối đa 15 từ, nêu đúng giá trị thông số làm căn cứ (VD "RTX 4060, RAM 16GB đủ chơi game nặng").
- "mismatch": chỉ xét các thông số trong "Thông số bắt buộc". Ghi {khóa: giá trị thực tế} khi bảng thông số ghi RÕ một giá trị KHÁC yêu cầu; giá trị thực tế phải chép NGUYÊN VĂN từ bảng. Không chắc hoặc bảng không ghi -> không đưa khóa đó vào."""

SYSTEM_PROMPT = f"""Bạn chấm mức phù hợp của sản phẩm với nhu cầu người mua, CHỈ dựa trên bảng thông số được cung cấp.

Quy tắc:
{_FIT_RULES}

Chỉ trả về JSON, không markdown:
{{"products": [{{"id": "...", "fit": 7, "reason": "...", "mismatch": {{}}}}]}}"""

SCREEN_SYSTEM_PROMPT = f"""Bạn thẩm định danh sách sản phẩm cào từ sàn TMĐT cho một yêu cầu mua sắm. Với TỪNG sản phẩm làm hai việc.

1. "keep": có đúng là THỨ người dùng muốn mua không.
   - Người dùng tìm sản phẩm chính: chỉ giữ chính sản phẩm đó, nguyên chiếc, dùng độc lập được. LOẠI phụ kiện ăn theo
     (thứ dùng CHO / GẮN VÀO / BẢO VỆ / TƯƠNG THÍCH VỚI sản phẩm: ốp lưng, bao da, dán cường lực, cáp sạc, dây đeo, túi đựng...),
     hàng mô hình / đồ chơi bản sao, vỏ hộp, linh kiện rã máy, và mặt hàng khác loại dù tên có chứa từ khóa.
   - Người dùng CHỦ ĐÍCH tìm phụ kiện / vật tư (yêu cầu ghi rõ): đối tượng chính là chính loại phụ kiện đó; giữ đúng loại
     phụ kiện, LOẠI thiết bị chính và mặt hàng khác loại (VD tìm "lót chuột" thì loại "USB Bluetooth ... - miếng lót chuột", chuột, bàn phím).
   - KHÔNG loại sản phẩm chính chỉ vì tên không ghi rõ thông số: xác minh thông số là việc của bước 2.

2. Với sản phẩm giữ lại, chấm "fit", "reason", "mismatch" CHỈ dựa trên bảng thông số:
{_FIT_RULES}

Chỉ trả về JSON, không markdown, đủ mọi sản phẩm:
{{"products": [{{"id": "...", "keep": true, "fit": 7, "reason": "...", "mismatch": {{}}}}, {{"id": "...", "keep": false}}]}}"""

SCREEN_BUDGET_SECONDS = 10.0  # một lần gọi làm cả lọc lẫn chấm; quá thì giữ nguyên danh sách, không có điểm
MAX_SCREEN_PRODUCTS = 24

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def need_text(criteria: Any) -> str:
    """Nhu cầu của người dùng thành một câu cho LLM: ngành hàng, mục đích, ưu tiên, ngân sách."""
    parts = []
    category = getattr(criteria, "category_name", None) or getattr(criteria, "target_entity", None)
    if category and category not in ("Tất cả", "Khác"):
        parts.append(f"Loại sản phẩm: {category}")
    if getattr(criteria, "usage_purpose", None):
        parts.append(f"Mục đích sử dụng: {criteria.usage_purpose}")
    priority = getattr(criteria, "priority", None) or "best_value"
    parts.append(f"Ưu tiên: {PRIORITY_NEEDS.get(priority, PRIORITY_NEEDS['best_value'])}")
    if getattr(criteria, "max_price", None):
        parts.append(f"Ngân sách tối đa: {criteria.max_price:,.0f} đ")
    return "; ".join(parts)


def _compact_specs(specs: Any) -> dict[str, str]:
    if not isinstance(specs, dict):
        return {}
    items = [(str(k), str(v)[:MAX_SPEC_VALUE_CHARS]) for k, v in specs.items() if k and v]
    return dict(items[:MAX_SPEC_ITEMS])


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", "", str(s).lower())


def _cache_key(p: dict[str, Any], need: str, wanted: dict[str, str]) -> str:
    specs = json.dumps(_compact_specs(p.get("specs")), ensure_ascii=False, sort_keys=True)
    return json.dumps([p.get("id"), need, wanted, specs, p.get("currentPrice")], ensure_ascii=False, sort_keys=True)


def _cache_get(key: str) -> dict[str, Any] | None:
    hit = _cache.get(key)
    return hit[1] if hit and time.time() - hit[0] < CACHE_TTL_SECONDS else None


def _cache_put(key: str, value: dict[str, Any]) -> None:
    if len(_cache) >= CACHE_MAX_ENTRIES:
        for k in sorted(_cache, key=lambda k: _cache[k][0])[: CACHE_MAX_ENTRIES // 4]:
            del _cache[k]
    _cache[key] = (time.time(), value)


def _user_prompt(need: str, wanted: dict[str, str], products: list[dict[str, Any]], header: str = "") -> str:
    items = [
        {
            "id": str(p.get("id")),
            "name": str(p.get("name", ""))[:120],
            "price": float(p.get("currentPrice") or 0),
            "specs": _compact_specs(p.get("specs")),
        }
        for p in products
    ]
    required = json.dumps(wanted, ensure_ascii=False) if wanted else "không có"
    return (
        f"{header}Nhu cầu: {need}\nThông số bắt buộc: {required}\n\n"
        f"Sản phẩm:\n{json.dumps(items, ensure_ascii=False, separators=(',', ':'))}"
    )


def _parse_result(entry: dict[str, Any], product: dict[str, Any], wanted: dict[str, str]) -> dict[str, Any]:
    """Một dòng kết quả của LLM -> {"fit", "mismatch"} đã kiểm tra (giá trị thực tế phải có trong bảng thông số)."""
    out: dict[str, Any] = {"fit": None, "mismatch": {}}
    fit = entry.get("fit")
    if isinstance(fit, (int, float)) and not isinstance(fit, bool):
        reason = str(entry.get("reason") or "").strip()[:MAX_REASON_CHARS]
        out["fit"] = {"score": max(0.0, min(1.0, float(fit) / 10)), "reason": reason}
    spec_text = _norm(" ".join(f"{k} {v}" for k, v in (product.get("specs") or {}).items()))
    mismatch = entry.get("mismatch") if isinstance(entry.get("mismatch"), dict) else {}
    for key, actual in mismatch.items():
        actual = str(actual or "").strip()
        if key in wanted and actual and _norm(actual) in spec_text:
            out["mismatch"][key] = actual
    return out


async def _judge(need: str, wanted: dict[str, str], products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    chat_model = get_chat_model(temperature=0.0, fast=True)
    if not chat_model:
        return {}
    raw = await ask_llm(
        chat_model,
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=_user_prompt(need, wanted, products))],
    )
    rows = parse_llm_json(raw).get("products")
    if not isinstance(rows, list):
        return {}
    by_id = {str(p.get("id")): p for p in products}
    results = {}
    for entry in rows:
        if isinstance(entry, dict) and str(entry.get("id")) in by_id:
            pid = str(entry["id"])
            results[pid] = _parse_result(entry, by_id[pid], wanted)
    return results


async def assess(
    products: list[dict[str, Any]], criteria: Any, wanted: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Bản sao các sản phẩm kèm specFit / specMismatch (xem đầu file); lỗi thì trả bản sao không có hai trường này."""
    out = [{k: v for k, v in p.items() if k not in ("specFit", "specMismatch")} for p in products]
    if not criteria:
        return out
    wanted = wanted or {}
    need = need_text(criteria)
    with_specs = [p for p in out if _compact_specs(p.get("specs"))][:MAX_PRODUCTS]

    results: dict[str, dict[str, Any]] = {}
    todo = []
    for p in with_specs:
        cached = _cache_get(_cache_key(p, need, wanted))
        if cached is not None:
            results[str(p.get("id"))] = cached
        else:
            todo.append(p)
    if todo:
        try:
            fresh = await asyncio.wait_for(_judge(need, wanted, todo), FIT_BUDGET_SECONDS)
        except (LLMError, TimeoutError) as e:
            logger.warning(f"[SpecFit] Bỏ qua bước chấm theo thông số ({type(e).__name__}: {e})")
            fresh = {}
        for p in todo:
            pid = str(p.get("id"))
            if pid in fresh:
                results[pid] = fresh[pid]
                _cache_put(_cache_key(p, need, wanted), fresh[pid])

    for p in out:
        _annotate(p, results.get(str(p.get("id"))))
    if results:
        logger.info(f"[SpecFit] Chấm {len(results)}/{len(out)} sản phẩm theo thông số cho nhu cầu: {need}")
    return out


def _annotate(p: dict[str, Any], r: dict[str, Any] | None) -> None:
    if not r:
        return
    if r["fit"]:
        p["specFit"] = r["fit"]
    if r["mismatch"]:
        p["specMismatch"] = r["mismatch"]


async def screen(
    products: list[dict[str, Any]], criteria: Any, query: str, wanted: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """MỘT lần gọi LLM vừa lọc (bỏ phụ kiện ăn theo / hàng khác loại) vừa chấm specFit / specMismatch.

    Trả về bản sao các sản phẩm được giữ, theo thứ tự cũ. Không có LLM / LLM lỗi / quá thời gian -> giữ nguyên
    danh sách và không chấm điểm (như bộ lọc cũ khi LLM lỗi). LLM bỏ sót sản phẩm nào thì coi như loại.
    """
    out = [{k: v for k, v in p.items() if k not in ("specFit", "specMismatch")} for p in products]
    if not out:
        return out
    wanted = wanted or {}
    need = need_text(criteria) if criteria else "không nêu"
    accessory = bool(criteria and getattr(criteria, "is_accessory", False))
    header = f'Yêu cầu tìm kiếm: "{query}"\n' + (
        "Người dùng CHỦ ĐÍCH tìm phụ kiện / vật tư này: giữ đúng loại phụ kiện đó, loại mặt hàng khác loại.\n"
        if accessory
        else ""
    )
    batch = out[:MAX_SCREEN_PRODUCTS]
    chat_model = get_chat_model(temperature=0.0, fast=True)
    if not chat_model:
        return out
    messages = [
        SystemMessage(content=SCREEN_SYSTEM_PROMPT),
        HumanMessage(content=_user_prompt(need, wanted, batch, header)),
    ]
    try:
        raw = parse_llm_json(await asyncio.wait_for(ask_llm(chat_model, messages), SCREEN_BUDGET_SECONDS))
    except (LLMError, TimeoutError) as e:
        logger.warning(f"[SpecFit] Không lọc + chấm được ({type(e).__name__}: {e}), giữ nguyên danh sách")
        return out
    rows = raw.get("products")
    if not isinstance(rows, list):
        logger.warning("[SpecFit] Phản hồi lọc + chấm không có danh sách sản phẩm, giữ nguyên danh sách")
        return out

    by_id = {str(p.get("id")): p for p in batch}
    kept_ids = set()
    for entry in rows:
        pid = str(entry.get("id")) if isinstance(entry, dict) else ""
        if pid not in by_id or entry.get("keep") is False:
            continue
        kept_ids.add(pid)
        p = by_id[pid]
        if _compact_specs(p.get("specs")):
            result = _parse_result(entry, p, wanted)
            _cache_put(_cache_key(p, need, wanted), result)  # lượt sau trúng cache tìm kiếm khỏi chấm lại
            _annotate(p, result)
    kept = [p for p in batch if str(p.get("id")) in kept_ids]
    logger.info(
        f"[SpecFit] Lọc + chấm '{query}': giữ {len(kept)}/{len(batch)} sản phẩm, "
        f"chấm {sum('specFit' in p for p in kept)} theo nhu cầu: {need}"
    )
    return kept
