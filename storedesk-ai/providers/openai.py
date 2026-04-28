from .base import LLMProvider
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any, Optional

class OpenAIProvider(LLMProvider):
    def __init__(self, name: str, model: str, api_key: str):
        super().__init__(name, model, supports_tool_calling=True, api_key=api_key)
        self.llm = ChatOpenAI(temperature=0, openai_api_key=api_key, model_name=model)

    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        print(f"[OPENAI] 🤖 Processing request with {len(messages)} messages")
        
        lc_messages = []
        for msg in messages:
            # Handle both LangChain message objects and dictionary messages
            if hasattr(msg, 'content'):
                # LangChain message object
                if hasattr(msg, 'type') and msg.type == 'system':
                    lc_messages.append(SystemMessage(content=msg.content))
                elif hasattr(msg, 'type') and msg.type == 'human':
                    lc_messages.append(HumanMessage(content=msg.content))
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    lc_messages.append(AIMessage(content=msg.content))
                else:
                    lc_messages.append(msg)
            else:
                # Dictionary message
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    lc_messages.append(SystemMessage(content=msg["content"]))

        if tools:
            print(f"[OPENAI] 🔧 Tool calling requested with {len(tools)} tools")
            try:
                # Use direct tool calling with OpenAI
                response = await self.llm.ainvoke(lc_messages, tools=tools)
                print(f"[OPENAI] ✅ Tool calling response received")

                # Handle tool calls
                if response.tool_calls:
                    tool_calls_data = []
                    for tc in response.tool_calls:
                        tool_calls_data.append({
                            "function": {
                                "name": tc.name,
                                "arguments": tc.args
                            }
                        })
                    print(f"[OPENAI] 🔧 Tool calls detected: {len(tool_calls_data)}")
                    return {"content": response.content, "tool_calls": tool_calls_data, "provider": self.name}
                else:
                    print(f"[OPENAI] 💬 No tool calls - text response only")
                    return {"content": response.content, "provider": self.name}
                    
            except Exception as e:
                print(f"[OPENAI] ❌ Tool calling failed: {str(e)}")
                # Fallback to non-tool call
                response = await self.llm.ainvoke(lc_messages)

        else:
            print(f"[OPENAI] 💬 Invoking model {self.model} (no tools)")
            response = await self.llm.ainvoke(lc_messages)
        
        print(f"[OPENAI] 📦 Raw response type: {type(response)}")
        print(f"[OPENAI] 💬 Response content: {response.content[:200]}..." if len(response.content) > 200 else f"[OPENAI] Response content: {response.content}")

        # Return response with provider name for tracing
        result = {"content": response.content, "provider": self.name}
        print(f"[OPENAI] ✅ Returning response with provider: {self.name}")
        
        return result
