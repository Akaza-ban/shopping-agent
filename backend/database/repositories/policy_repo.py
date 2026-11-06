import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from ..connection import async_session
from ..models import PlatformModel, PolicyChunkModel, PolicyDocumentModel, PolicyTermModel

SUMMARY = "summary"


def term_to_dict(term: PolicyTermModel, platform: PlatformModel, url: str, doc_type: Optional[str] = None) -> Dict[str, Any]:
    """Cùng dạng với PlatformPolicy ở frontend."""
    return {
        "platformId": term.platform_id,
        "platformName": platform.name,
        "platformType": platform.type,
        "category": term.category,
        "returnWindowDays": term.return_window_days,
        "freeReturn": bool(term.free_return),
        "returnConditions": json.loads(term.return_conditions_json or "[]"),
        "returnShippingFee": term.return_shipping_fee,
        "refundTime": term.refund_time,
        "defectExchange": term.defect_exchange,
        "warrantyHandling": term.warranty_handling,
        "exceptions": json.loads(term.exceptions_json or "[]"),
        "policyUrl": url or platform.home_url,
        "lastChecked": term.last_checked.strftime("%d/%m/%Y") if term.last_checked else "",
        "verified": doc_type is not None and doc_type != SUMMARY,
    }


class PolicyRepository:
    """Kho chính sách đổi trả, bảo hành của các nền tảng."""

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def is_empty(self) -> bool:
        async with self.session_factory() as session:
            return not await session.scalar(select(func.count()).select_from(PlatformModel))

    async def upsert_platform_policy(self, platform: Dict[str, Any], terms: Dict[str, Any], content: str,
                                     category: str = "all", last_checked=None) -> None:
        """Ghi (hoặc thay) nền tảng, trang chính sách, điều khoản chuẩn hóa và các đoạn văn của trang."""
        async with self.session_factory() as session:
            p = await session.get(PlatformModel, platform["id"])
            if p is None:
                p = PlatformModel(id=platform["id"])
                session.add(p)
            p.name, p.type, p.home_url = platform["name"], platform["type"], platform["url"]

            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            doc = await session.scalar(select(PolicyDocumentModel).where(
                PolicyDocumentModel.platform_id == p.id, PolicyDocumentModel.doc_type == SUMMARY))
            if doc is None:
                doc = PolicyDocumentModel(platform_id=p.id, doc_type=SUMMARY)
                session.add(doc)
            doc.title = f"Chính sách đổi trả và bảo hành - {p.name}"
            doc.url = platform["url"]
            if doc.content_hash != digest:
                doc.content, doc.content_hash = content, digest
                await self._replace_chunks(session, doc, [x.strip() for x in content.split("\n\n")])
            await session.flush()

            term = await session.scalar(select(PolicyTermModel).where(
                PolicyTermModel.platform_id == p.id, PolicyTermModel.category == category))
            if term is None:
                term = PolicyTermModel(platform_id=p.id, category=category)
                session.add(term)
            term.document_id = doc.id
            self._fill_terms(term, terms)
            if last_checked is not None:
                term.last_checked = last_checked
            await session.commit()

    async def list_policies(self, platform_ids: Optional[List[str]] = None, category: str = "all") -> List[Dict[str, Any]]:
        """Điều khoản của từng nền tảng: ưu tiên bản riêng của ngành hàng, không có thì dùng bản 'all'."""
        async with self.session_factory() as session:
            q = (select(PolicyTermModel, PlatformModel, PolicyDocumentModel.url, PolicyDocumentModel.doc_type)
                 .join(PlatformModel, PlatformModel.id == PolicyTermModel.platform_id)
                 .outerjoin(PolicyDocumentModel, PolicyDocumentModel.id == PolicyTermModel.document_id)
                 .where(PolicyTermModel.category.in_({"all", category})))
            if platform_ids is not None:
                q = q.where(PolicyTermModel.platform_id.in_(platform_ids))
            chosen: Dict[str, Dict[str, Any]] = {}
            for term, platform, url, doc_type in (await session.execute(q.order_by(PlatformModel.created_at, PlatformModel.id))).all():
                if term.platform_id not in chosen or term.category != "all":
                    chosen[term.platform_id] = term_to_dict(term, platform, url, doc_type)
            return list(chosen.values())

    async def list_chunks(self, platform_ids: List[str]) -> List[Dict[str, Any]]:
        """Đoạn văn của trang chính sách gốc; nền tảng chưa có trang gốc thì dùng bản tóm tắt."""
        async with self.session_factory() as session:
            rows = (await session.execute(
                select(PolicyChunkModel, PolicyDocumentModel.url, PolicyDocumentModel.doc_type, PolicyDocumentModel.title)
                .join(PolicyDocumentModel, PolicyDocumentModel.id == PolicyChunkModel.document_id)
                .where(PolicyChunkModel.platform_id.in_(platform_ids))
                .order_by(PolicyChunkModel.platform_id, PolicyChunkModel.document_id, PolicyChunkModel.position))).all()
        official = {c.platform_id for c, _, doc_type, _ in rows if doc_type != SUMMARY}
        return [{"id": c.id, "platformId": c.platform_id, "text": c.text, "url": url, "title": title}
                for c, url, doc_type, title in rows if doc_type != SUMMARY or c.platform_id not in official]

    async def upsert_document(self, platform_id: str, doc_type: str, title: str, url: str, chunks: List[str]) -> bool:
        """Lưu trang chính sách gốc (khóa: nền tảng + url). Trả về True nếu nội dung mới hoặc đã thay đổi."""
        content = "\n\n".join(chunks)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        async with self.session_factory() as session:
            doc = await session.scalar(select(PolicyDocumentModel).where(
                PolicyDocumentModel.platform_id == platform_id, PolicyDocumentModel.url == url,
                PolicyDocumentModel.doc_type != SUMMARY))
            if doc is None:
                doc = PolicyDocumentModel(platform_id=platform_id, url=url)
                session.add(doc)
            doc.doc_type, doc.title, doc.fetched_at = doc_type, title, datetime.utcnow()
            changed = doc.content_hash != digest
            if changed:
                doc.content, doc.content_hash = content, digest
                await self._replace_chunks(session, doc, chunks)
            await session.commit()
            return changed

    @staticmethod
    async def _replace_chunks(session, doc: PolicyDocumentModel, texts: List[str]) -> None:
        if doc.id is not None:
            for c in await session.scalars(select(PolicyChunkModel).where(PolicyChunkModel.document_id == doc.id)):
                await session.delete(c)
        await session.flush()
        for i, text in enumerate(t for t in texts if t):
            session.add(PolicyChunkModel(document_id=doc.id, platform_id=doc.platform_id, position=i, text=text))

    async def official_documents(self) -> List[Dict[str, Any]]:
        """Trang chính sách gốc đã tải, kèm tên nền tảng (đầu vào cho bước rút điều khoản)."""
        async with self.session_factory() as session:
            rows = (await session.execute(
                select(PolicyDocumentModel, PlatformModel.name)
                .join(PlatformModel, PlatformModel.id == PolicyDocumentModel.platform_id)
                .where(PolicyDocumentModel.doc_type != SUMMARY)
                .order_by(PolicyDocumentModel.platform_id, PolicyDocumentModel.id))).all()
            return [{"id": d.id, "platformId": d.platform_id, "platformName": name, "url": d.url,
                     "content": d.content or "", "fetchedAt": d.fetched_at} for d, name in rows]

    async def upsert_terms(self, platform_id: str, terms: Dict[str, Any], document_id: Optional[int] = None,
                           category: str = "all", last_checked=None) -> None:
        """Ghi điều khoản chuẩn hóa của một nền tảng (không đụng tới trang chính sách và các đoạn văn)."""
        async with self.session_factory() as session:
            term = await session.scalar(select(PolicyTermModel).where(
                PolicyTermModel.platform_id == platform_id, PolicyTermModel.category == category))
            if term is None:
                term = PolicyTermModel(platform_id=platform_id, category=category)
                session.add(term)
            self._fill_terms(term, terms)
            if document_id is not None:
                term.document_id = document_id
            if last_checked is not None:
                term.last_checked = last_checked
            await session.commit()

    @staticmethod
    def _fill_terms(term: PolicyTermModel, terms: Dict[str, Any]) -> None:
        term.return_window_days = terms["return_window_days"]
        term.free_return = terms["free_return"]
        term.return_conditions_json = json.dumps(terms["return_conditions"], ensure_ascii=False)
        term.return_shipping_fee = terms["return_shipping_fee"]
        term.refund_time = terms["refund_time"]
        term.defect_exchange = terms["defect_exchange"]
        term.warranty_handling = terms["warranty_handling"]
        term.exceptions_json = json.dumps(terms["exceptions"], ensure_ascii=False)

    async def list_documents(self) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            rows = (await session.execute(
                select(PolicyDocumentModel, func.count(PolicyChunkModel.id))
                .outerjoin(PolicyChunkModel, PolicyChunkModel.document_id == PolicyDocumentModel.id)
                .group_by(PolicyDocumentModel.id).order_by(PolicyDocumentModel.platform_id))).all()
            return [{"platformId": d.platform_id, "docType": d.doc_type, "title": d.title, "url": d.url,
                     "chars": len(d.content or ""), "chunks": n,
                     "fetchedAt": d.fetched_at.isoformat() if d.fetched_at else None} for d, n in rows]


policy_repository = PolicyRepository()
