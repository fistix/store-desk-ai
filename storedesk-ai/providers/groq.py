from .base import LLMProvider
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any, Optional

class GroqProvider(LLMProvider):
    def __init__(self, name: str, model: str, api_key: str):
        super().__init__(name, model, supports_tool_calling=True, api_key=api_key)
        self.llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name=model)

    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        if tools:
            # Groq native tool calling
            # Bind tools to the LLM for tool calling
            llm_with_tools = self.llm.bind_tools(tools)
            response = await llm_with_tools.invoke(lc_messages)
            
            if response.tool_calls:
                tool_calls_data = []
                for tc in response.tool_calls:
                    tool_calls_data.append({
                        "function": {
                            "name": tc.name,
                            "arguments": tc.args
                        }
                    })
                return {"tool_calls": tool_calls_data}
            else:
                return {"content": response.content}

        else:
            response = await self.llm.invoke(lc_messages)
            return {"content": response.content}
