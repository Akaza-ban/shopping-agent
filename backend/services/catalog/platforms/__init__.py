"""Các sàn TMĐT / chuỗi bán lẻ (Strategy + Registry):"""
from services.catalog.platforms.base import PlatformAdapter
from services.catalog.platforms.registry import (
    all_platforms, display_names, get_platform, platform_for_url, platform_ids, platform_mentioned, resolve_targets,
)

__all__ = [
    "PlatformAdapter", "all_platforms", "display_names", "get_platform", "platform_for_url", "platform_ids",
    "platform_mentioned", "resolve_targets",
]
