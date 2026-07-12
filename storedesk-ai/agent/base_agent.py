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
from security.prompt_sanitizer import PromptSanitizer, SecurityException
from security.security_monitor import security_monitor

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
        
        # Initialize security components
        self.prompt_sanitizer = PromptSanitizer()
        
        self.graph = self._build_graph()

    def _initialize_tools(self) -> List[BaseTool]:
        return [tool_class() for name, tool_class in self.tool_registry.items()]

    def _get_langchain_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_langchain_tool() for tool in self.tools]

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        pass

    async def _call_llm(self, state: AgentState, tools_available: bool = False, tools: Optional[List[Dict[str, Any]]] = None, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        user_id = state.get("userContext", {}).get("user_id", "unknown")
        
        # If custom prompt is provided, use it directly
        if custom_prompt:
            print(f"[BASE_AGENT] 📝 Using custom prompt for LLM call")
            
            # Sanitize custom prompt
            try:
                sanitized_prompt = self.prompt_sanitizer.sanitize_input(custom_prompt, user_id)
                messages = [HumanMessage(content=sanitized_prompt)]
            except SecurityException as e:
                await security_monitor.log_security_event(
                    "agent_custom_prompt_injection",
                    user_id,
                    custom_prompt[:100],
                    str(e),
                    "HIGH"
                )
                # Return safe response
                return {"content": "I cannot process that request. Please provide a different input.", "provider": "security_block"}
            
            if tools_available and tools:
                print(f"[BASE_AGENT] 🔧 Passing {len(tools)} tools to LLM")
                llm_response = await provider_manager.complete(messages, tools)
            else:
                print(f"[BASE_AGENT] 💬 No tools available - calling LLM without tools")
                llm_response = await provider_manager.complete(messages)
            
            # Validate LLM response
            return self.prompt_sanitizer.validate_llm_response(llm_response, user_id)
        
        # Create enhanced system prompt with context
        system_prompt = self.system_prompt
        
        # Add selected product IDs to system prompt if available
        selected_product_ids = state.get("userContext", {}).get("selected_product_ids", [])
        if selected_product_ids:
            system_prompt += (
                f"\n\nAvailable Product IDs (already selected by the user): {selected_product_ids}\n"
                "When the user refers to 'selected products' or does not name specific IDs, "
                "pass these exact IDs as productIds in the tool call. "
                "Do not ask the user for product IDs when this list is present."
            )
        
        messages = [SystemMessage(content=system_prompt)]
        
        # Sanitize conversation history
        for msg in state["conversationHistory"]:
            if msg["role"] == "user":
                try:
                    sanitized_content = self.prompt_sanitizer.sanitize_input(msg["content"], user_id)
                    messages.append(HumanMessage(content=sanitized_content))
                except SecurityException as e:
                    await security_monitor.log_security_event(
                        "agent_history_injection",
                        user_id,
                        msg["content"][:100],
                        str(e),
                        "HIGH"
                    )
                    # Skip suspicious message
                    continue
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Sanitize current user message
        try:
            sanitized_user_message = self.prompt_sanitizer.sanitize_input(state["userMessage"], user_id)
            messages.append(HumanMessage(content=sanitized_user_message))
        except SecurityException as e:
            await security_monitor.log_security_event(
                "agent_message_injection",
                user_id,
                state["userMessage"][:100],
                str(e),
                "HIGH"
            )
            # Return safe response
            return {"content": "I cannot process that request. Please provide a different input.", "provider": "security_block"}

        if tools_available and tools:
            print(f"[BASE_AGENT] 🔧 Passing {len(tools)} tools to LLM")
            llm_response = await provider_manager.complete(messages, tools)
            
            # Validate LLM response
            validated_response = self.prompt_sanitizer.validate_llm_response(llm_response, user_id)
            
            # Fill in product IDs from context if tool calls were parsed
            if "tool_calls" in validated_response and validated_response["tool_calls"]:
                selected_product_ids = state.get("userContext", {}).get("selected_product_ids", [])
                print(f"[BASE_AGENT] 🔧 Filling product IDs: {selected_product_ids}")
                
                for tool_call in validated_response["tool_calls"]:
                    args = tool_call["function"]["arguments"]
                    
                    # Validate tool parameters
                    if not self.prompt_sanitizer.validate_tool_parameters(args, user_id):
                        await security_monitor.log_security_event(
                            "agent_invalid_tool_params",
                            user_id,
                            str(args)[:100],
                            "Invalid tool parameters detected",
                            "HIGH"
                        )
                        # Remove invalid tool call
                        validated_response["tool_calls"].remove(tool_call)
                        continue
                    
                    # Fill product IDs from user context when LLM omitted them
                    product_ids = args.get("productIds")
                    bulk = args.get("bulkStockMonitoring") or args.get("bulkPriceMonitoring") or {}
                    apply_to_all = bool(bulk.get("isApplyToAllProducts", False))

                    if not apply_to_all and selected_product_ids:
                        if not product_ids:
                            args["productIds"] = list(selected_product_ids)
                            print(f"[BASE_AGENT] ✅ Filled empty productIds from context: {args['productIds']}")
                        else:
                            print(f"[BASE_AGENT] 🔧 Using LLM-provided product IDs: {product_ids}")
                    elif "productIds" not in args and selected_product_ids and not apply_to_all:
                        args["productIds"] = list(selected_product_ids)
                        print(f"[BASE_AGENT] ✅ Added missing productIds from context: {args['productIds']}")
            
            return validated_response
        else:
            print(f"[BASE_AGENT] 💬 No tools available - calling LLM without tools")
            llm_response = await provider_manager.complete(messages)
            
            # Validate LLM response
            return self.prompt_sanitizer.validate_llm_response(llm_response, user_id)

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
