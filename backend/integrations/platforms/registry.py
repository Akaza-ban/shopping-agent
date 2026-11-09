"""Danh sách các sàn hệ thống hỗ trợ: nơi duy nhất cần sửa khi thêm / bỏ một sàn."""

from collections.abc import Iterable

from integrations.platforms.base import PlatformAdapter
from integrations.platforms.cellphones import CellphonesAdapter
from integrations.platforms.fpt import FptAdapter
from integrations.platforms.mwg import DMX, TGDD
from integrations.platforms.tiki import TikiAdapter

# Thứ tự = thứ tự đan xen kết quả khi tìm trên mọi sàn
PLATFORMS: list[PlatformAdapter] = [TGDD, DMX, TikiAdapter(), FptAdapter(), CellphonesAdapter()]
_BY_ID = {p.id: p for p in PLATFORMS}


def all_platforms() -> list[PlatformAdapter]:
    return list(PLATFORMS)


def platform_ids() -> list[str]:
    return [p.id for p in PLATFORMS]


def get_platform(platform_id: str | None) -> PlatformAdapter | None:
    return _BY_ID.get((platform_id or "").lower())


def platform_for_url(url: str | None) -> PlatformAdapter | None:
    return next((p for p in PLATFORMS if p.owns_url(url)), None)


def platform_mentioned(text: str) -> PlatformAdapter | None:
    """Sàn được nhắc tới trong câu hỏi ("mua ở điện máy xanh"); None nếu không nhắc sàn nào."""
    return next((p for p in PLATFORMS if p.mentioned_in(text)), None)


def resolve_targets(names: Iterable[str]) -> list[PlatformAdapter]:
    """Tên sàn trong tiêu chí tìm kiếm ("all", "tgdd", "thegioididong"...) -> các sàn tương ứng; tên lạ bị bỏ qua."""
    names = [n.lower().strip() for n in names if n]
    if not names or "all" in names:
        return all_platforms()
    return [p for p in PLATFORMS if any(n == p.id or n in p.aliases for n in names)]


def display_names(separator: str = ", ") -> str:
    return separator.join(p.name if p.id != "tiki" else "Tiki" for p in PLATFORMS)
