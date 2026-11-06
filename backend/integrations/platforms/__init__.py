"""Các sàn TMĐT / chuỗi bán lẻ: mỗi sàn một adapter (tìm kiếm, đọc trang chi tiết, đọc giá), tra theo mã sàn / link qua registry."""
from integrations.platforms.base import PlatformAdapter
from integrations.platforms.registry import (
    all_platforms, display_names, get_platform, platform_for_url, platform_ids, platform_mentioned, resolve_targets,
)

__all__ = [
    "PlatformAdapter", "all_platforms", "display_names", "get_platform", "platform_for_url", "platform_ids",
    "platform_mentioned", "resolve_targets",
]
