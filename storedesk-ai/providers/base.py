from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    def __init__(self, name: str, model: str, supports_tool_calling: bool, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.name = name
        self.model = model
        self.supports_tool_calling = supports_tool_calling
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        pass
