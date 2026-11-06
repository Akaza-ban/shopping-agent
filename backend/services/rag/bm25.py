"""Chỉ mục BM25 Okapi trong RAM cho toàn bộ tài liệu của collection (vài nghìn sản phẩm)."""
import math
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from services.rag.text import index_tokens, strip_accents, words

Meta = Dict[str, Any]

class BM25Index:
    def __init__(self, ids: List[str], texts: List[str], metas: List[Meta], k1: float = 1.5, b: float = 0.75):
        self.ids = ids
        self.metas = metas
        self.k1, self.b = k1, b
        self._docs = [Counter(index_tokens(words(t))) for t in texts]
        self._lengths = [sum(d.values()) for d in self._docs]
        self._avg_len = (sum(self._lengths) / len(self._lengths)) if self._lengths else 1.0
        self._pos = {pid: i for i, pid in enumerate(ids)}

        df = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def top(self, terms: List[str], n: int, keep: Optional[Callable[[Meta], bool]] = None) -> List[str]:
        """Id của tối đa n tài liệu điểm cao nhất (điểm > 0) thỏa `keep`."""
        tokens = index_tokens(terms)
        scored = []
        for i, doc in enumerate(self._docs):
            if keep and not keep(self.metas[i]):
                continue
            score = sum(self._term_score(doc, i, t) for t in tokens if t in doc)
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [self.ids[i] for _, i in scored[:n]]

    def _term_score(self, doc: Counter, i: int, token: str) -> float:
        tf = doc[token]
        norm = 1 - self.b + self.b * self._lengths[i] / self._avg_len
        return self._idf[token] * tf * (self.k1 + 1) / (tf + self.k1 * norm)

    def meta(self, pid: str) -> Optional[Meta]:
        i = self._pos.get(pid)
        return self.metas[i] if i is not None else None

    def coverage(self, pid: str, terms: List[str]) -> float:
        """Tỉ lệ từ khóa truy vấn có trong tài liệu (có dấu hoặc không dấu)."""
        i = self._pos.get(pid)
        if i is None or not terms:
            return 0.0
        doc = self._docs[i]
        return sum(1 for t in terms if t in doc or strip_accents(t) in doc) / len(terms)
