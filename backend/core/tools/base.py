from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    async def run(self, **kwargs) -> dict[str, Any]:
        """Thực thi tool"""
        pass
