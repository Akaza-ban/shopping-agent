import json
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select

from ..connection import async_session
from ..errors import raises_database_error
from ..models import CategoryMappingModel


@raises_database_error
class CategoryMappingRepository:
    """Bảng quy đổi danh mục của sàn -> ngành hàng chuẩn."""

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def all(self) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            rows = (await session.scalars(select(CategoryMappingModel))).all()
            return [{"source_key": r.source_key, "category": r.category, "is_accessory": bool(r.is_accessory),
                     "noun": r.product_noun or "", "decided_by": r.decided_by} for r in rows]

    async def save(self, rows: List[Dict[str, Any]]) -> None:
        """Ghi kết quả quy đổi của LLM; dòng đã sửa tay (decided_by = manual) giữ nguyên."""
        async with self.session_factory() as session:
            for r in rows:
                m = await session.get(CategoryMappingModel, r["source_key"])
                if m is not None and m.decided_by == "manual":
                    continue
                if m is None:
                    m = CategoryMappingModel(source_key=r["source_key"])
                    session.add(m)
                m.platform = r["platform"]
                m.label = r["label"]
                m.samples_json = json.dumps(r.get("samples", []), ensure_ascii=False)
                m.category = r["category"]
                m.is_accessory = r["is_accessory"]
                m.product_noun = r.get("noun") or ""
                m.decided_by = r.get("decided_by", "llm")
                m.updated_at = datetime.utcnow()
            await session.commit()


category_repository = CategoryMappingRepository()
