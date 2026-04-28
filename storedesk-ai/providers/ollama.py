from .base import LLMProvider
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
import json

class OllamaProvider(LLMProvider):
    def __init__(self, name: str, model: str, base_url: str):
        super().__init__(name, model, supports_tool_calling=False, base_url=base_url) # Ollama uses prompt-based for now
        self.llm = ChatOllama(model=model, base_url=base_url, temperature=0)

    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        if tools:
            # For Ollama, we need to inject the tool schema into the prompt
            tool_prompt = "\nTOOLS:\n"
            for tool in tools:
                tool_prompt += f"\nTool Name: {tool['function']['name']}\n"
                tool_prompt += f"Description: {tool['function']['description']}\n"
                tool_prompt += f"Parameters: {json.dumps(tool['function']['parameters'])}\n"
            tool_prompt += "\nWhen you need to use a tool, respond with a JSON object like this: {\"tool_calls\": [{\"function\": {\"name\": \"tool_name\", \"arguments\": {\"arg1\": \"value1\", ...}}}]}\n"
            
            lc_messages[-1].content += tool_prompt

        response = await self.llm.invoke(lc_messages)
        content = response.content

        # Attempt to parse as tool call
        if tools and "tool_calls" in content:
            try:
                parsed_content = json.loads(content)
                if "tool_calls" in parsed_content:
                    return {"tool_calls": parsed_content["tool_calls"]}
            except json.JSONDecodeError:
                pass # Not a JSON tool call, treat as normal content

        return {"content": content}
