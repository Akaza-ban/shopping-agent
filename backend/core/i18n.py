"""Câu chữ agent hiển thị cho người dùng, theo ngôn ngữ (core/locales/vi.json, en.json).

Thiếu khóa ở tiếng Anh thì dùng tiếng Việt. Thêm câu mới: thêm khóa vào cả hai file JSON.
"""

import json
import pathlib
from typing import Any

DEFAULT_LANGUAGE = "vi"
_LOCALE_DIR = pathlib.Path(__file__).parent / "locales"
_LOCALES: dict[str, dict[str, Any]] = {
    path.stem: json.loads(path.read_text(encoding="utf-8")) for path in _LOCALE_DIR.glob("*.json")
}


def _lookup(key: str, language: str) -> Any:
    table = _LOCALES.get(language) or _LOCALES[DEFAULT_LANGUAGE]
    return table[key] if key in table else _LOCALES[DEFAULT_LANGUAGE][key]


def tr(key: str, language: str, **values: Any) -> str:
    """Một câu theo ngôn ngữ; `values` điền vào chỗ {tên} trong câu."""
    text = _lookup(key, language)
    return text.format(**values) if values else text


def tr_list(key: str, language: str) -> list[str]:
    """Một danh sách câu theo ngôn ngữ (bản sao, sửa thoải mái)."""
    return list(_lookup(key, language))
