from typing import Dict, List, Optional
from core.state import MessageItem

class SessionMemoryManager:
    """Quản lý lịch sử hội thoại ngắn hạn (Short-term conversation memory)."""

    def __init__(self):
        self._sessions: Dict[str, List[MessageItem]] = {}

    def get_messages(self, session_id: str) -> List[MessageItem]:
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, message: MessageItem):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(message)

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

session_memory = SessionMemoryManager()
