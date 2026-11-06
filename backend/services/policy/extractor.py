import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_chat_model

MAX_CONTENT_CHARS = 20000

EXTRACT_PROMPT = """Bạn đọc trang chính sách đổi trả, bảo hành của một nhà bán lẻ và rút ra điều khoản cho SẢN PHẨM MỚI thuộc nhóm hàng chính (điện thoại, laptop, máy tính bảng). Nhóm hàng khác có quy định khác thì ghi ngắn vào exceptions.
Chỉ dùng thông tin có trong trang. Không có thông tin thì để chuỗi rỗng (hoặc 0 với số ngày). Mỗi chuỗi tối đa 25 từ, tiếng Việt.
Trả về đúng một JSON, không markdown:
{"return_window_days": số ngày tối đa được đổi/trả sản phẩm lỗi nhà sản xuất,
 "free_return": true nếu trả hàng KHÔNG do lỗi mà không mất phí, ngược lại false,
 "return_conditions": [tối đa 3 điều kiện sản phẩm phải đáp ứng],
 "return_shipping_fee": "phí/cách thức gửi trả hàng",
 "refund_time": "mức phí hoặc thời gian hoàn tiền",
 "defect_exchange": "quy định khi sản phẩm lỗi nhà sản xuất",
 "warranty_handling": "ai tiếp nhận bảo hành, ở đâu",
 "exceptions": [tối đa 4 lưu ý quan trọng: phí trả hàng không lỗi, nhóm hàng không áp dụng...],
 "evidence": [2-4 câu trích nguyên văn ngắn từ trang làm căn cứ cho các con số ở trên]}"""

_STR_FIELDS = ("return_shipping_fee", "refund_time", "defect_exchange", "warranty_handling")
_LIST_FIELDS = ("return_conditions", "exceptions", "evidence")


def parse_terms(raw: str) -> Dict[str, Any]:
    """JSON của LLM -> dict điều khoản đúng kiểu; thiếu hoặc sai kiểu thì báo lỗi."""
    text = raw.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("LLM không trả về JSON")
    data = json.loads(m.group(0))
    out: Dict[str, Any] = {
        "return_window_days": int(data.get("return_window_days") or 0),
        "free_return": bool(data.get("free_return")),
    }
    for f in _STR_FIELDS:
        out[f] = str(data.get(f) or "").strip()
    for f in _LIST_FIELDS:
        value = data.get(f) or []
        out[f] = [str(x).strip() for x in (value if isinstance(value, list) else [value]) if str(x).strip()]
    if not 0 <= out["return_window_days"] <= 400:
        raise ValueError(f"số ngày đổi trả bất thường: {out['return_window_days']}")
    return out


def unsupported_numbers(terms: Dict[str, Any], content: str) -> List[str]:
    """Các con số (ngày, %) trong điều khoản mà không xuất hiện trong trang gốc -> có thể LLM tự bịa."""
    fields = [terms[f] for f in _STR_FIELDS] + terms["return_conditions"] + terms["exceptions"]
    found = set(re.findall(r"\d+(?:[.,]\d+)?\s*%?", " ".join(fields)))
    if terms["return_window_days"]:
        found.add(str(terms["return_window_days"]))
    flat = re.sub(r"\s+", "", content)
    return sorted(n.strip() for n in found if re.sub(r"\s+", "", n) not in flat)


async def extract_terms(platform_name: str, content: str) -> Dict[str, Any]:
    model = get_chat_model(temperature=0.0)
    if model is None:
        raise RuntimeError("chưa cấu hình LLM")
    response = await model.ainvoke([
        SystemMessage(content=EXTRACT_PROMPT),
        HumanMessage(content=f"Nhà bán lẻ: {platform_name}\n\nNội dung trang:\n{content[:MAX_CONTENT_CHARS]}"),
    ])
    terms = parse_terms(str(getattr(response, "content", response)))
    terms["unsupported_numbers"] = unsupported_numbers(terms, content)
    return terms
