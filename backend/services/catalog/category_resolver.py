import asyncio
import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from integrations.llm import ask_llm, get_chat_model
from integrations.platforms import get_platform, platform_for_url
from shared.categories import CANONICAL, LABELS, canonical_code
from shared.exceptions import DatabaseError, LLMError

logger = logging.getLogger("category_resolver")

BATCH_SIZE = 15
LLM_TIMEOUT_SECONDS = 12.0
MAX_SAMPLES = 3

CLASSIFY_PROMPT = """Bạn quy đổi danh mục sản phẩm của các sàn TMĐT Việt Nam sang ngành hàng chuẩn của hệ thống.
Ngành hàng chuẩn (chỉ dùng đúng các mã này):
{codes}
Mỗi danh mục có "key", "label" (tên hoặc đường dẫn danh mục của sàn) và "samples" (vài sản phẩm thuộc danh mục).
- Dựa vào cả label và samples. Phụ kiện / linh kiện / vật tư (ốp lưng, cáp sạc, miếng dán, balo laptop, chuột, router...)
  thì category = "other" và accessory = true. Tai nghe, loa là "audio", không phải phụ kiện.
- Thiết bị chính nhưng không thuộc ngành nào ở trên (máy ảnh, máy chơi game, đồ chơi...) thì "other", accessory = false.
- "noun": tên loại sản phẩm ngắn, tiếng Việt có dấu (VD "Máy giặt", "Robot hút bụi", "Laptop") khi samples THIẾU tên loại
  (VD "LG Inverter 9 kg", "MSI Prestige 14"); để "" khi samples đã nêu rõ loại ("Tai nghe Sony...", "Robot hút bụi Xiaomi...")
  hoặc tên tự nói lên loại (điện thoại "iPhone 16", "Samsung Galaxy S26"). Không dùng tên dòng / series / hệ điều hành.
Trả về đúng một mảng JSON, không markdown, mỗi danh mục một phần tử, giữ nguyên "key" như đầu vào;
"category" là MÃ tiếng Anh ở trên (VD "phones"), không phải phần mô tả:
[{{"key": "<key>", "category": "<mã>", "accessory": true/false, "noun": "<tên loại hoặc rỗng>"}}, ...]"""

SAME_KIND_PROMPT = """Người mua muốn so sánh các sản phẩm dưới đây. Chúng có cùng một loại sản phẩm, phục vụ cùng một nhu cầu
để so sánh trực tiếp với nhau được không (VD hai điện thoại: có; điện thoại với laptop: không; robot hút bụi với tai nghe: không)?
Trả về đúng một JSON: {"same_kind": true/false}"""


@dataclass(frozen=True)
class CategoryMapping:
    category: str
    is_accessory: bool
    noun: str = ""


class CategoryResolver:
    def __init__(self, repository=None):
        self._repository = repository
        self._cache: dict[str, CategoryMapping] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    @property
    def repository(self):
        if self._repository is None:
            from database.repositories.category_repo import category_repository

            self._repository = category_repository
        return self._repository

    # tra bảng
    @staticmethod
    def source_of(product: Mapping[str, Any]) -> tuple[str, str, str] | None:
        """(khóa, mô tả, mã sàn) của danh mục sản phẩm theo sàn bán; None nếu sàn không cho biết danh mục."""
        platform = platform_for_url(product.get("externalUrl")) or get_platform(product.get("platform"))
        if platform is None:
            return None
        source = platform.category_source(product)
        return (source[0], source[1], platform.id) if source else None

    def lookup(self, product: Mapping[str, Any]) -> CategoryMapping | None:
        source = self.source_of(product)
        return self._cache.get(source[0]) if source else None

    def remember(self, mappings: dict[str, tuple]) -> None:
        """Ghi thẳng vào bảng trong bộ nhớ (dùng khi nạp từ CSDL và trong test): {khóa: (ngành, phụ kiện[, tên loại])}."""
        for key, value in mappings.items():
            category, accessory, noun = (tuple(value) + ("",))[:3]
            if category in CANONICAL:
                self._cache[key] = CategoryMapping(category, bool(accessory), noun or "")

    async def load(self) -> None:
        """Nạp bảng quy đổi đã lưu (gọi lúc khởi động; resolve() tự gọi nếu chưa nạp)."""
        try:
            rows = await self.repository.all()
        except DatabaseError as e:
            logger.warning(f"Không nạp được bảng quy đổi danh mục: {e}")
            return
        self.remember({r["source_key"]: (r["category"], r["is_accessory"], r.get("noun") or "") for r in rows})
        self._loaded = True
        logger.info(f"Đã nạp {len(rows)} quy đổi danh mục")

    async def resolve(self, products: list[dict[str, Any]]) -> None:
        """Quy đổi các danh mục chưa gặp của danh sách sản phẩm (một lần gọi LLM cho mỗi BATCH_SIZE danh mục)."""
        if not self._loaded:
            await self.load()
        pending: dict[str, dict[str, Any]] = {}
        for p in products:
            source = self.source_of(p)
            if not source or source[0] in self._cache:
                continue
            item = pending.setdefault(
                source[0], {"key": source[0], "label": source[1], "platform": source[2], "samples": []}
            )
            name = str(p.get("name") or "").strip()
            if name and name not in item["samples"] and len(item["samples"]) < MAX_SAMPLES:
                item["samples"].append(name)
        if not pending:
            return
        async with self._lock:
            items = [v for k, v in pending.items() if k not in self._cache]
            for i in range(0, len(items), BATCH_SIZE):
                await self._classify(items[i : i + BATCH_SIZE])

    async def _classify(self, items: list[dict[str, Any]]) -> None:
        model = get_chat_model(temperature=0.0, fast=True)
        if model is None:
            return
        codes = "\n".join(f"- {code}: {label}" for code, label in LABELS.items())
        payload = [{"key": i["key"], "label": i["label"], "samples": i["samples"]} for i in items]
        try:
            raw = await ask_llm(
                model,
                [
                    SystemMessage(content=CLASSIFY_PROMPT.format(codes=codes)),
                    HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
                ],
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except LLMError as e:
            logger.warning(f"LLM quy đổi danh mục lỗi, để chưa rõ ngành hàng: {e}")
            return
        decided = parse_classification(raw)
        missing = [i["key"] for i in items if i["key"] not in decided]
        if missing:
            logger.warning(
                f"LLM không quy đổi được {len(missing)}/{len(items)} danh mục (sẽ hỏi lại lần sau): "
                f"{missing[:5]} | phản hồi: {raw[:300]!r}"
            )
        rows = []
        for item in items:
            mapping = decided.get(item["key"])
            if mapping is None:
                continue
            self._cache[item["key"]] = mapping
            rows.append(
                {
                    **item,
                    "source_key": item["key"],
                    "category": mapping.category,
                    "is_accessory": mapping.is_accessory,
                    "noun": mapping.noun,
                }
            )
        if rows:
            try:
                await self.repository.save(rows)
            except DatabaseError as e:
                logger.warning(f"Không lưu được quy đổi danh mục: {e}")
            logger.info(
                f"Đã quy đổi {len(rows)} danh mục mới: " + ", ".join(f"{r['key']} -> {r['category']}" for r in rows)
            )

    #  cùng loại hay không
    async def same_kind(self, products: list[dict[str, Any]]) -> bool | None:
        """Các sản phẩm có cùng loại để so sánh trực tiếp không; None nếu không hỏi được LLM."""
        model = get_chat_model(temperature=0.0, fast=True)
        if model is None:
            return None
        names = [str(p.get("name") or "") for p in products]
        try:
            raw = await ask_llm(
                model,
                [
                    SystemMessage(content=SAME_KIND_PROMPT),
                    HumanMessage(content=json.dumps(names, ensure_ascii=False)),
                ],
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except LLMError as e:
            logger.warning(f"LLM kiểm tra cùng loại lỗi: {e}")
            return None
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except ValueError:
            data = None
        value = data.get("same_kind") if isinstance(data, dict) else None
        return value if isinstance(value, bool) else None


def parse_classification(raw: str) -> dict[str, CategoryMapping]:
    """Câu trả lời của LLM (mảng hoặc đối tượng JSON) -> {khóa danh mục: CategoryMapping}; sai định dạng -> {}."""
    m = re.search(r"[\[{].*[\]}]", raw or "", re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return {}
    if isinstance(data, dict):
        data = [{"key": k, **v} for k, v in data.items() if isinstance(v, dict)]
    out: dict[str, CategoryMapping] = {}
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict) or not row.get("key"):
            continue
        code = _to_code(row.get("category"))
        if code:
            out[str(row["key"])] = CategoryMapping(
                code, row.get("accessory") is True, str(row.get("noun") or "").strip()
            )
    return out


_BY_LABEL = {label.lower(): code for code, label in LABELS.items()}


def _to_code(value: Any) -> str | None:
    """Mã ngành hàng; model đôi khi trả phần mô tả ("điện thoại / máy tính bảng") hoặc số ít ("laptop")."""
    text = str(value or "").strip()
    if text in CANONICAL:
        return text
    code = _BY_LABEL.get(text.lower()) or canonical_code(text)
    return code if code in CANONICAL else None


category_resolver = CategoryResolver()


def with_noun(name: str, noun: str) -> str:
    """Ghép tên loại vào đầu tên sản phẩm nếu tên chưa có ("LG Inverter 9 kg" -> "Máy giặt LG Inverter 9 kg")."""
    name = (name or "").strip()
    if not noun or noun.lower() in name.lower():
        return name
    return f"{noun} {name}"
