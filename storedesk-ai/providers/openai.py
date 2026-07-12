import json
from .base import LLMProvider
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any, Optional


class OpenAIProvider(LLMProvider):
    def __init__(self, name: str, model: str, api_key: str):
        super().__init__(name, model, supports_tool_calling=True, api_key=api_key)
        self.llm = ChatOpenAI(
            temperature=0,
            openai_api_key=api_key,
            model_name=model,
            streaming=False,
        )

    def _to_lc_messages(self, messages: List[Any]) -> List[Any]:
        lc_messages = []
        for msg in messages:
            # Handle both LangChain message objects and dictionary messages
            if hasattr(msg, "content"):
                if hasattr(msg, "type") and msg.type == "system":
                    lc_messages.append(SystemMessage(content=msg.content))
                elif hasattr(msg, "type") and msg.type == "human":
                    lc_messages.append(HumanMessage(content=msg.content))
                elif hasattr(msg, "type") and msg.type == "ai":
                    lc_messages.append(AIMessage(content=msg.content))
                else:
                    lc_messages.append(msg)
            else:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                elif role == "system":
                    lc_messages.append(SystemMessage(content=content))
        return lc_messages

    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        tool_calls_data: List[Dict[str, Any]] = []

        # Preferred LangChain shape: response.tool_calls
        raw_tool_calls = getattr(response, "tool_calls", None) or []
        for tc in raw_tool_calls:
            if isinstance(tc, dict):
                name = tc.get("name")
                args = tc.get("args", {})
            else:
                name = getattr(tc, "name", None)
                args = getattr(tc, "args", {})
            if name:
                tool_calls_data.append({
                    "function": {
                        "name": name,
                        "arguments": args if isinstance(args, dict) else {},
                    }
                })

        if tool_calls_data:
            return tool_calls_data

        # Fallback: OpenAI-style tool_calls in additional_kwargs
        additional = getattr(response, "additional_kwargs", {}) or {}
        for tc in additional.get("tool_calls", []) or []:
            function = tc.get("function", {}) if isinstance(tc, dict) else {}
            name = function.get("name")
            raw_args = function.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args if isinstance(raw_args, dict) else {}
            if name:
                tool_calls_data.append({
                    "function": {
                        "name": name,
                        "arguments": args,
                    }
                })

        return tool_calls_data

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        print(f"[OPENAI] 🤖 Processing request with {len(messages)} messages")
        lc_messages = self._to_lc_messages(messages)

        if tools:
            print(f"[OPENAI] 🔧 Binding {len(tools)} tools via bind_tools()")
            for i, tool in enumerate(tools):
                tool_name = (
                    tool.get("function", {}).get("name")
                    if isinstance(tool, dict)
                    else getattr(tool, "name", "unknown")
                )
                print(f"[OPENAI] 🔧 Tool {i + 1}: {tool_name}")

            try:
                # bind_tools is required for ChatOpenAI — tools= on ainvoke is not enough
                llm_with_tools = self.llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(lc_messages)
                print("[OPENAI] ✅ Tool calling response received")

                tool_calls_data = self._extract_tool_calls(response)
                content = response.content or ""

                if tool_calls_data:
                    print(f"[OPENAI] 🔧 Tool calls detected: {len(tool_calls_data)}")
                    for i, tc in enumerate(tool_calls_data):
                        print(
                            f"[OPENAI] 🔧 Tool {i + 1}: "
                            f"{tc['function']['name']} args={tc['function']['arguments']}"
                        )
                    return {
                        "content": content,
                        "tool_calls": tool_calls_data,
                        "provider": self.name,
                    }

                print("[OPENAI] 💬 No tool calls - text response only")
                return {"content": content, "provider": self.name}

            except Exception as e:
                print(f"[OPENAI] ❌ Tool calling failed: {str(e)}")
                # Fallback to non-tool call so the agent can still respond
                response = await self.llm.ainvoke(lc_messages)
                return {
                    "content": response.content or "",
                    "provider": self.name,
                }

        print(f"[OPENAI] 💬 Invoking model {self.model} (no tools)")
        response = await self.llm.ainvoke(lc_messages)
        return {"content": response.content or "", "provider": self.name}
