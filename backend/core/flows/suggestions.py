"""2-3 câu hỏi gợi ý nhanh (quick chips) sau mỗi câu trả lời, theo ngữ cảnh:

link vừa đọc -> hỏi về link đó; 2+ sản phẩm -> so sánh hai cái đầu; 1 sản phẩm -> hỏi sâu về nó;
không có sản phẩm -> gợi ý theo chủ đề câu hỏi (điện thoại, laptop, mặc định).
Câu chữ nằm ở core/locales/*.json (khóa "suggest.*").
"""

import re

from memory.session_manager import session_memory

from ..i18n import tr_list
from ..state import AgentState, ProductItemModel

# Từ chỉ loại sản phẩm ở đầu tên, bỏ đi khi rút gọn tên ("Tai nghe Chụp Tai Sony WH1000XM6" -> "Sony WH1000XM6")
GENERIC_NAME_WORDS = re.compile(
    r"^(?:tai|nghe|chụp|nhét|không|dây|laptop|điện|thoại|máy|giặt|tính|bảng|tivi|smart|loa|đồng|hồ|thông|minh|tủ|lạnh|new|full|box|chính|hãng)$",
    re.IGNORECASE,
)
NAME_PREVIEW_CHARS = 25


def short_name(name: str) -> str:
    """'Tai nghe Chụp Tai Sony WH1000XM6' -> 'Sony WH1000XM6'."""
    words = name.split()
    start = next((i for i, w in enumerate(words) if not GENERIC_NAME_WORDS.match(w)), 0)
    return " ".join(words[start : start + 2]) or name[:15]


def _context_products(state: AgentState) -> list[ProductItemModel]:
    """Sản phẩm của lượt này; không có thì lấy sản phẩm đã đề xuất ở lượt trước trong phiên."""
    if state.found_products or not state.session_id:
        return state.found_products
    return [ProductItemModel(**p) for p in session_memory.get_last_products(state.session_id) or []]


def generate(state: AgentState) -> list[str]:
    if state.clarification:
        return []
    lang = state.language
    if state.intent == "parse_link" and state.found_products:
        name = state.found_products[0].name[:NAME_PREVIEW_CHARS]
        return [q.format(name=name) for q in tr_list("suggest.link", lang)]
    products = _context_products(state)
    if len(products) >= 2:
        a, b = short_name(products[0].name), short_name(products[1].name)
        return [q.format(a=a, b=b) for q in tr_list("suggest.pair", lang)]
    if len(products) == 1:
        p = products[0]
        return [
            q.format(name=p.name[:NAME_PREVIEW_CHARS], platform=p.platformName) for q in tr_list("suggest.single", lang)
        ]
    query = state.user_query.lower()
    if any(w in query for w in tr_list("suggest.phone_words", lang)):
        return tr_list("suggest.phones", lang)
    if "laptop" in query:
        return tr_list("suggest.laptops", lang)
    return tr_list("suggest.default", lang)
