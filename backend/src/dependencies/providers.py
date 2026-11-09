"""Các đối tượng nặng dùng chung, tạo một lần và truyền vào route qua Depends().

Test thay thế bằng `app.dependency_overrides[get_workflow] = lambda: fake`.
"""

from functools import lru_cache

from core.graph import ShopAIAgentWorkflow


@lru_cache(maxsize=1)
def get_workflow() -> ShopAIAgentWorkflow:
    """Workflow LangGraph của trợ lý (dựng graph một lần cho cả server)."""
    return ShopAIAgentWorkflow()
