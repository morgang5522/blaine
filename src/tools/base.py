from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """Abstract Base Class for tools registered with Blaine AI Assistant."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool function exposed to LLM."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema / Dict describing tool parameter requirements."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Executes the tool logic with given arguments."""
        pass
