from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def to_langchain_tool(self) -> Dict[str, Any]:
        # This method should be implemented by subclasses to define the tool schema
        # for LangChain/LLM consumption. This is a generic representation.
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
