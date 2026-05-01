from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from providers.manager import provider_manager
from agent.base_tool import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.pydantic_v1 import BaseModel, Field
import operator
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, END
from config.settings import settings

class AgentState(TypedDict):
    userMessage: str
    userContext: Dict[str, Any]
    conversationHistory: Annotated[List[Dict[str, Any]], operator.add]
    pendingConfirmation: Optional[Dict[str, Any]]
    toolCallsMade: List[Dict[str, Any]]  # Removed operator.add to prevent accumulation
    toolResults: Annotated[List[Dict[str, Any]], operator.add]
    iterationCount: int
    finalResponse: Optional[Dict[str, Any]]
    clarificationQuestion: Optional[str]
    requiresConfirmation: bool
    routing_decision: Optional[str]
    matched_keywords: List[str]
    intent_confidence: float

class BaseAgent(ABC):
    def __init__(self, name: str, description: str, system_prompt: str, tool_registry: Dict[str, Type[BaseTool]]):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        self.tools = self._initialize_tools()
        self.llm_with_tools = None # Will be bound dynamically
        self.graph = self._build_graph()

    def _initialize_tools(self) -> List[BaseTool]:
        return [tool_class() for name, tool_class in self.tool_registry.items()]

    def _get_langchain_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_langchain_tool() for tool in self.tools]

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        pass

    async def _call_llm(self, state: AgentState, tools_available: bool = False, tools: Optional[List[Dict[str, Any]]] = None, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        # If custom prompt is provided, use it directly
        if custom_prompt:
            print(f"[BASE_AGENT] 📝 Using custom prompt for LLM call")
            messages = [HumanMessage(content=custom_prompt)]
            
            if tools_available and tools:
                print(f"[BASE_AGENT] 🔧 Passing {len(tools)} tools to LLM")
                llm_response = await provider_manager.complete(messages, tools)
            else:
                print(f"[BASE_AGENT] 💬 No tools available - calling LLM without tools")
                llm_response = await provider_manager.complete(messages)
            
            return llm_response
        
        # Create enhanced system prompt with context
        system_prompt = self.system_prompt
        
        # Add selected product IDs to system prompt if available
        selected_product_ids = state.get("userContext", {}).get("selected_product_ids", [])
        if selected_product_ids:
            system_prompt += f"\n\nAvailable Product IDs: {selected_product_ids}\nUse these product IDs when calling tools that require productIds parameter."
        
        messages = [SystemMessage(content=system_prompt)]
        for msg in state["conversationHistory"]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=state["userMessage"]))

        if tools_available and tools:
            print(f"[BASE_AGENT] 🔧 Passing {len(tools)} tools to LLM")
            llm_response = await provider_manager.complete(messages, tools)
            
            # Fill in product IDs from context if tool calls were parsed
            if "tool_calls" in llm_response and llm_response["tool_calls"]:
                selected_product_ids = state.get("userContext", {}).get("selected_product_ids", [])
                print(f"[BASE_AGENT] 🔧 Filling product IDs: {selected_product_ids}")
                
                for tool_call in llm_response["tool_calls"]:
                    args = tool_call["function"]["arguments"]
                    # Only fill product IDs if they're empty and not "all"
                    if "productIds" in args and args["productIds"] == [] and args.get("productIds") != "all":
                        args["productIds"] = selected_product_ids
                        print(f"[BASE_AGENT] ✅ Updated tool call with product IDs: {args}")
        else:
            print(f"[BASE_AGENT] 💬 No tools available - calling LLM without tools")
            llm_response = await provider_manager.complete(messages)
        
        return llm_response

    async def _execute_tool(self, state: AgentState) -> Dict[str, Any]:
        tool_calls = state["toolCallsMade"]
        tool_results = state.get("toolResults", [])
        
        # Execute all tool calls that don't have corresponding results yet
        results = []
        for i, tool_call in enumerate(tool_calls):
            # Skip if we already have a result for this tool call
            if i < len(tool_results):
                continue
            
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            tool_instance = next((t for t in self.tools if t.name == tool_name), None)
            if not tool_instance:
                results.append({"tool_name": tool_name, "success": False, "message": f"Tool {tool_name} not found."})
            else:
                result = await tool_instance.execute(tool_args, state["userContext"])
                results.append({**result, "tool_name": tool_name})
        
        return {"toolResults": results}

    async def invoke(self, state: AgentState) -> AgentState:
        app = self.graph.compile()
        final_state = await app.ainvoke(state, config={"max_iterations": settings.REQUEST_MAX_ITERATIONS})
        return final_state
