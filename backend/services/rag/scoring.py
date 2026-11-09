"""Ứng viên truy xuất, ngưỡng chấp nhận và điểm khớp hiển thị."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Thresholds:
    """Khoảng cách cosine của bge-m3, hiệu chỉnh bằng `python -m scripts.rag.eval --calibrate`."""

    vec_accept: float = 0.45  # đủ gần về nghĩa -> nhận luôn
    vec_weak: float = 0.50
    lex_support: float = 0.67  # tỉ lệ từ khóa cần có để "đỡ" kết quả hơi xa
    lex_only: float = 0.75


@dataclass
class Candidate:
    id: str
    meta: dict[str, Any]
    rrf: float
    coverage: float
    distance: float | None = None  # None khi embedding API không dùng được

    def accepted(self, t: Thresholds) -> bool:
        if self.distance is None:
            return self.coverage >= t.lex_only
        return (
            self.distance <= t.vec_accept
            or (self.distance <= t.vec_weak and self.coverage >= t.lex_support)
            or self.coverage >= 0.999  # có đủ mọi từ khóa (VD đúng mã model)
        )

    def match_score(self, t: Thresholds) -> int:
        """Điểm khớp 60–99% hiển thị cho người dùng."""
        if self.distance is None:
            return int(60 + 30 * self.coverage)
        closeness = (t.vec_weak - self.distance) / t.vec_weak
        return max(60, min(99, int(70 + 60 * closeness + 10 * self.coverage)))
