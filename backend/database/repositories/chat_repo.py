import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from ..connection import async_session
from ..errors import raises_database_error
from ..models import ChatSessionModel, ChatMessageModel, ConversationStateModel

logger = logging.getLogger("chat_repo")

def _stored_json(text: Optional[str], opener: str, empty: Any) -> Any:
    """Danh sách / đối tượng JSON lưu trong cột text; cột trống hoặc không đúng dạng (opener "[" / "{") -> empty."""
    return json.loads(text) if text and text.startswith(opener) else empty


def _message(session_id: str, sender: str, text: str, now: datetime, msg_id: str,
             products: Optional[List[Dict[str, Any]]] = None, criteria: Optional[Dict[str, Any]] = None) -> ChatMessageModel:
    return ChatMessageModel(
        id=msg_id,
        session_id=session_id,
        sender=sender,
        text=text,
        products_json=json.dumps(products or [], ensure_ascii=False),
        criteria_json=json.dumps(criteria or {}, ensure_ascii=False),
        timestamp=now.strftime("%H:%M"),
        created_at=now,
    )


@raises_database_error
class ChatRepository:
    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def get_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            try:
                stmt = (
                    select(ChatMessageModel)
                    .where(ChatMessageModel.session_id == session_id)
                    .order_by(ChatMessageModel.created_at.asc())
                )
                res = await session.execute(stmt)
                records = res.scalars().all()
                # Lấy limit bản ghi gần nhất
                recent_records = records[-limit:] if len(records) > limit else records
                return [
                    {
                        "id": r.id,
                        "session_id": r.session_id,
                        "sender": r.sender,
                        "text": r.text,
                        "products": _stored_json(r.products_json, "[", []),
                        "criteria": _stored_json(r.criteria_json, "{", {}),
                        "timestamp": r.timestamp or r.created_at.strftime("%H:%M")
                    }
                    for r in recent_records
                ]
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                logger.warning(f"Lỗi lấy tin nhắn session {session_id}: {e}")
                return []

    async def get_last_context(self, session_id: str) -> Dict[str, Any]:
        async with self.session_factory() as session:
            try:
                # Tìm tin nhắn gần nhất có chứa sản phẩm
                stmt = (
                    select(ChatMessageModel)
                    .where(ChatMessageModel.session_id == session_id)
                    .order_by(ChatMessageModel.created_at.desc())
                    .limit(5)
                )
                res = await session.execute(stmt)
                recent = res.scalars().all()

                last_products = []
                last_criteria = {}

                for msg in recent:
                    try:
                        last_products = last_products or _stored_json(msg.products_json, "[", [])
                    except ValueError:
                        pass
                    try:
                        last_criteria = last_criteria or _stored_json(msg.criteria_json, "{", {})
                    except ValueError:
                        pass

                return {
                    "last_products": last_products,
                    "last_criteria": last_criteria
                }
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                logger.warning(f"Lỗi lấy ngữ cảnh gần nhất session {session_id}: {e}")
                return {"last_products": [], "last_criteria": {}}

    async def save_turn(
        self,
        session_id: str,
        user_text: str,
        ai_text: str,
        products: Optional[List[Dict[str, Any]]] = None,
        criteria: Optional[Dict[str, Any]] = None
    ) -> None:
        """Lưu tin nhắn người dùng và câu trả lời của AI (kèm sản phẩm, tiêu chí); tạo phiên chat nếu chưa có."""
        async with self.session_factory() as session:
            try:
                now = datetime.utcnow()
                if await session.get(ChatSessionModel, session_id) is None:
                    session.add(ChatSessionModel(id=session_id, title=user_text[:40] if user_text else "Đoạn chat mới",
                                                 summary="", created_at=now))
                now_ms = int(time.time() * 1000)
                session.add(_message(session_id, "user", user_text, now, f"msg-user-{now_ms}"))
                session.add(_message(session_id, "ai", ai_text, now, f"msg-ai-{now_ms + 1}", products, criteria))
                await session.commit()
                logger.info(f"[ChatRepo] Đã lưu lượt hội thoại cho session '{session_id}' vào SQLite.")
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                await session.rollback()
                logger.error(f"Lỗi khi lưu lượt hội thoại: {e}")

    async def claim_session(self, session_id: str, user_id: str, title: str = "") -> bool:
        """Gán hội thoại cho người dùng (tạo mới nếu chưa có); False nếu hội thoại thuộc người khác."""
        async with self.session_factory() as session:
            existing = await session.get(ChatSessionModel, session_id)
            if existing is None:
                session.add(ChatSessionModel(id=session_id, title=(title or "Đoạn chat mới")[:40],
                                             summary="", created_at=datetime.utcnow(), user_id=user_id))
            elif existing.user_id is None:
                existing.user_id = user_id
            elif existing.user_id != user_id:
                return False
            await session.commit()
            return True

    async def get_session_owner(self, session_id: str) -> Optional[str]:
        async with self.session_factory() as session:
            existing = await session.get(ChatSessionModel, session_id)
            return existing.user_id if existing else None

    async def get_conversation_state(self, session_id: str) -> Dict[str, Any]:
        async with self.session_factory() as session:
            try:
                record = await session.get(ConversationStateModel, session_id)
                return json.loads(record.state_json) if record and record.state_json else {}
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                logger.warning(f"Lỗi lấy trạng thái hội thoại session {session_id}: {e}")
                return {}

    async def save_conversation_state(self, session_id: str, state: Dict[str, Any]) -> None:
        async with self.session_factory() as session:
            try:
                record = await session.get(ConversationStateModel, session_id)
                payload = json.dumps(state, ensure_ascii=False)
                if record:
                    record.state_json = payload
                    record.updated_at = datetime.utcnow()
                else:
                    session.add(ConversationStateModel(session_id=session_id, state_json=payload, updated_at=datetime.utcnow()))
                await session.commit()
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                await session.rollback()
                logger.error(f"Lỗi khi lưu trạng thái hội thoại session {session_id}: {e}")

    async def clear_session(self, session_id: str) -> None:
        async with self.session_factory() as session:
            try:
                await session.execute(
                    delete(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
                )
                await session.execute(
                    delete(ConversationStateModel).where(ConversationStateModel.session_id == session_id)
                )
                await session.execute(
                    delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
                )
                await session.commit()
                logger.info(f"[ChatRepo] Đã xóa session '{session_id}'.")
            except (SQLAlchemyError, ValueError) as e:  # ValueError: cột JSON hỏng
                await session.rollback()
                logger.error(f"Lỗi khi xóa session {session_id}: {e}")

chat_repository = ChatRepository()
