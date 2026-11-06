from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Thực thi tool bất đồng bộ."""
        pass
