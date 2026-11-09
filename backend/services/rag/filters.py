"""Bộ lọc metadata dùng chung cho truy vấn vector (ChromaDB `where`) và BM25 (hàm Python)."""

import time
from dataclasses import dataclass, field
from typing import Any

from shared.categories import canonical_code

Meta = dict[str, Any]


@dataclass
class SearchFilters:
    category: str | None = None
    platform: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    max_age_days: int | None = None
    excluded_platforms: list[str] = field(default_factory=list)

    def _conditions(self) -> list[tuple[str, str, Any]]:
        """Danh sách (trường, toán tử, giá trị) theo cú pháp ChromaDB."""
        conds: list[tuple[str, str, Any]] = []
        cat = canonical_code(self.category)

        if cat and cat not in ("all", "other"):
            conds.append(("category", "$eq", cat))
        if self.platform and self.platform.lower() != "all":
            conds.append(("platform", "$eq", self.platform.lower().strip()))
        elif self.excluded_platforms:
            conds.append(("platform", "$nin", list(self.excluded_platforms)))
        if self.min_price:
            conds.append(("current_price", "$gte", float(self.min_price)))
        if self.max_price:
            conds.append(("current_price", "$lte", float(self.max_price)))
        if self.max_age_days:
            conds.append(("updated_at", "$gte", int(time.time()) - int(self.max_age_days) * 86400))
        return conds

    def where(self) -> dict[str, Any] | None:
        clauses = [{f: {op: v}} for f, op, v in self._conditions()]
        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def matcher(self):
        conds = self._conditions()

        def matches(meta: Meta) -> bool:
            return all(_OPS[op](meta.get(f), v) for f, op, v in conds)

        return matches


_OPS = {
    "$eq": lambda a, b: a == b,
    "$nin": lambda a, b: a not in b,
    "$gte": lambda a, b: float(a or 0) >= b,
    "$lte": lambda a, b: float(a or 0) <= b,
}
