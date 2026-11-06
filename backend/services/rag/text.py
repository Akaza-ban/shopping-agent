"""Tách từ tiếng Việt cho tìm kiếm từ khóa (BM25) và đo độ phủ từ khóa."""
import re
import unicodedata
from typing import List

STOP_WORDS = {
    "tìm", "mua", "cho", "tôi", "giúp", "bạn", "ở", "tại", "có", "giá", "tốt", "nhất", "các", "những",
    "cần", "muốn", "nào", "mẫu", "dòng", "loại", "shop", "shopai", "tư", "vấn", "em", "khoảng", "tầm",
    "dưới", "trên", "từ", "đến", "tới", "triệu", "nghìn", "rẻ", "đẹp", "và", "hoặc", "với", "một", "cái",
    "chiếc", "là", "thì", "nên", "hãy", "gợi", "ý", "sản", "phẩm", "hàng", "chính", "hãng", "mới",
}
_PRICE_PHRASE = re.compile(r"\d+([.,]\d+)?\s*(triệu|tr\b|củ|k\b|nghìn|ngàn|đ\b|vnđ|vnd)", re.IGNORECASE)


def strip_accents(word: str) -> str:
    word = word.replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


def words(text: str) -> List[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", (text or "").lower()))


def index_tokens(word_list: List[str]) -> List[str]:
    """Từ gốc + bản bỏ dấu + ghép cặp có chữ số ("rtx 4050" -> "rtx4050", "9 kg" -> "9kg")."""
    out = []
    for w in word_list:
        out.append(w)
        plain = strip_accents(w)
        if plain != w:
            out.append(plain)
    for a, b in zip(word_list, word_list[1:]):
        if len(a) <= 6 and any(c.isdigit() for c in a + b):
            out.append(strip_accents(a + b))
    return out


def query_terms(query: str) -> List[str]:
    """Từ khóa nội dung của truy vấn: bỏ từ dừng, cụm giá tiền, từ trùng."""
    terms: List[str] = []
    for w in words(_PRICE_PHRASE.sub(" ", query)):
        if w in STOP_WORDS or w in terms or (len(w) < 2 and not w.isdigit()):
            continue
        terms.append(w)
    return terms
