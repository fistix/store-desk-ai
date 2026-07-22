from agent.base_agent import BaseAgent, AgentState, HumanMessage, AIMessage, SystemMessage
from agent.domains.products import product_tool_registry
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from config.settings import settings
import logging
import re
import uuid

logger = logging.getLogger(__name__)


def describe_exception(exc: Exception) -> str:
    """Return a human-readable error string.

    Starlette's HTTPException has an empty ``str()`` but carries the useful
    message in ``.detail``. Falling back to ``repr`` guarantees at least the
    exception type is visible for otherwise message-less errors.
    """
    detail = getattr(exc, "detail", None)
    return str(detail) if detail else (str(exc) or repr(exc))

# Define the system prompt for the Product Agent
PRODUCT_AGENT_SYSTEM_PROMPT = (
    "You help with product management. "
    "ALWAYS use tools for enable/disable stock or price monitoring requests. "
    "Do not answer with plain text when a tool can fulfill the request.\n\n"
    "SELECTED PRODUCTS (CRITICAL):\n"
    "- Product IDs may be provided below as 'Available Product IDs'. These are already selected in the UI.\n"
    "- When the user says 'selected products', 'these products', or similar, call the tool immediately "
    "using those Available Product IDs. Do NOT ask the user to provide or confirm product IDs.\n"
    "- Never list Available Product IDs back and ask the user to pick — they are already selected.\n"
    "- Only ask for product IDs if Available Product IDs are missing AND the user did not say 'all products'.\n\n"
    "Tools:\n"
    "- stock_monitoring: Enable OR disable stock/quantity monitoring\n"
    "- price_monitoring: Enable OR disable price/margin monitoring\n\n"
    "Enable/disable mapping:\n"
    "- Enable stock/quantity → stock_monitoring with isQuantityEnabled=true and the requested threshold\n"
    "- Disable stock/quantity → stock_monitoring with isQuantityEnabled=false and quantityThreshold=0\n"
    "- Enable price/margin → price_monitoring with isPriceEnabled=true and the requested percentage\n"
    "- Disable price/margin → price_monitoring with isPriceEnabled=false and priceThresholdPercentage=0\n"
    "- 'all products' → isApplyToAllProducts=true (no productIds needed)\n"
    "- 'selected products' → isApplyToAllProducts=false and productIds=Available Product IDs\n"
    "- 'all monitoring' / 'both monitoring' / 'stock and price' → call BOTH stock_monitoring AND price_monitoring\n\n"
    "Examples of CLEAR requests (always call the matching tool):\n"
    "- 'Enable quantity monitoring for selected products with threshold 5'\n"
    "- 'Disable stock monitoring for all products'\n"
    "- 'Enable price margin monitoring at 8 percent for selected products'\n"
    "- 'Disable price monitoring for all products'\n"
    "- 'Disable all monitoring for all products' → call BOTH tools with isApplyToAllProducts=true and enabled=false\n"
    "- 'Monitor price changes for all products'\n\n"
    "Examples of UNCLEAR requests (ask clarification):\n"
    "- 'help me'\n"
    "- 'set a popular to 10 minutes'\n"
    "- 'thinking about prize money'\n"
)

class ProductsAgent(BaseAgent):
    def __init__(self, name: str = "products", description: str = "Manage product stock and price monitoring", system_prompt: str = PRODUCT_AGENT_SYSTEM_PROMPT):
        super().__init__(name, description, system_prompt, product_tool_registry.tools)

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("call_llm", self._call_llm_node)
        graph.add_node("execute_tool", self._execute_tool_node)
        graph.add_node("generate_response", self._generate_response_node)

        graph.set_entry_point("call_llm")

        graph.add_conditional_edges(
            "call_llm",
            self._decide_next_step,
            {
                "tool_code": "execute_tool",
                "final_response": "generate_response",
                "clarification": END # Or a clarification node if implemented
            },
        )
        graph.add_edge("execute_tool", "generate_response") # After tool execution, generate a response
        graph.add_edge("generate_response", END)

        return graph

    def _extract_threshold(self, message: str) -> Optional[float]:
        """Extract a numeric threshold from a monitoring request."""
        patterns = [
            r"threshold\s*(?:of|to|=|:)?\s*(\d+(?:\.\d+)?)",
            r"(?:below|under|at)\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:percent|%|units?)",
            r"(\d+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _is_disable_request(self, message: str) -> bool:
        return any(kw in message for kw in ["disable", "turn off", "stop", "remove", "deactivate"])

    def _is_enable_request(self, message: str) -> bool:
        return any(kw in message for kw in ["enable", "set", "monitor", "alert", "track", "turn on", "notify", "start"])

    def _build_monitoring_fallback_tool_call(self, state: AgentState) -> Optional[List[Dict[str, Any]]]:
        """
        Deterministic fallback when the LLM returns text instead of a tool call
        for a clear stock/price enable or disable request.
        """
        selected_product_ids = state.get("userContext", {}).get("selected_product_ids", []) or []
        message = (state.get("userMessage") or "").lower()

        is_stock = any(kw in message for kw in ["stock", "quantity", "inventory", "qty"])
        is_price = any(kw in message for kw in ["price", "margin", "profit"])
        if not is_stock and not is_price:
            return None
        # Prefer the more specific domain when both words appear
        if is_stock and is_price:
            if "price" in message or "margin" in message:
                is_stock = False
            else:
                is_price = False

        is_disable = self._is_disable_request(message)
        is_enable = self._is_enable_request(message) and not is_disable
        if not is_disable and not is_enable:
            return None

        apply_to_all = "all products" in message or ("all" in message and "product" in message)
        if not apply_to_all and not selected_product_ids:
            return None

        threshold = self._extract_threshold(message)
        if is_disable:
            threshold = 0 if threshold is None else threshold
        elif threshold is None:
            # Enable without a threshold is ambiguous — don't invent one
            return None

        product_ids = [] if apply_to_all else list(selected_product_ids)

        if is_stock:
            print(
                f"[PRODUCTS AGENT] 🛠️ Fallback tool call: stock_monitoring "
                f"(disable={is_disable}, all={apply_to_all}, threshold={threshold})"
            )
            return [{
                "id": f"fallback_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": "stock_monitoring",
                    "arguments": {
                        "productIds": product_ids,
                        "bulkStockMonitoring": {
                            "isApplyToAllProducts": apply_to_all,
                            "isQuantityEnabled": not is_disable,
                            "quantityThreshold": int(threshold),
                        },
                    },
                },
            }]

        print(
            f"[PRODUCTS AGENT] 🛠️ Fallback tool call: price_monitoring "
            f"(disable={is_disable}, all={apply_to_all}, threshold={threshold})"
        )
        return [{
            "id": f"fallback_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": "price_monitoring",
                "arguments": {
                    "productIds": product_ids,
                    "bulkPriceMonitoring": {
                        "isApplyToAllProducts": apply_to_all,
                        "isPriceEnabled": not is_disable,
                        "priceThresholdPercentage": float(threshold),
                    },
                },
            },
        }]

    def _llm_asked_for_product_ids(self, content: str) -> bool:
        if not content:
            return False
        lowered = content.lower()
        return any(
            phrase in lowered
            for phrase in [
                "which products",
                "specify which products",
                "provide the product",
                "product ids",
                "product id",
                "available list",
            ]
        )

    def _describe_monitoring_actions(self, tool_calls: List[Dict[str, Any]]) -> List[str]:
        """Build human-readable enable/disable labels for confirmation copy."""
        actions: List[str] = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_args = tool_call.get("function", {}).get("arguments", {}) or {}

            if tool_name == "stock_monitoring":
                bulk = tool_args.get("bulkStockMonitoring") or {}
                verb = "enable" if bulk.get("isQuantityEnabled", False) else "disable"
                actions.append(f"{verb} stock monitoring")
            elif tool_name == "price_monitoring":
                bulk = tool_args.get("bulkPriceMonitoring") or {}
                verb = "enable" if bulk.get("isPriceEnabled", False) else "disable"
                actions.append(f"{verb} price monitoring")

        return actions

    def _build_all_products_confirmation(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Describe every planned monitoring change when confirming an all-products update."""
        actions = self._describe_monitoring_actions(tool_calls)
        if not actions:
            return "Are you sure you want to update monitoring for all products?"

        verbs = {action.split(" ", 1)[0] for action in actions}
        kinds = [action.split(" ", 1)[1] for action in actions]

        if len(verbs) == 1:
            verb = next(iter(verbs))
            if len(kinds) == 1:
                target = kinds[0]
            elif kinds == ["stock monitoring", "price monitoring"] or set(kinds) == {
                "stock monitoring",
                "price monitoring",
            }:
                target = "stock and price monitoring"
            else:
                target = " and ".join(kinds)
            return f"Are you sure you want to {verb} {target} for all products?"

        return (
            "Are you sure you want to "
            + " and ".join(actions)
            + " for all products?"
        )

    def _process_tool_calls(self, state: AgentState, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply confirmation rules and return the next agent state update."""
        user_message = (state.get("userMessage") or "").lower()
        needs_all_products_confirmation = False

        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.get("function", {}).get("name", "unknown")
            tool_args = tool_call.get("function", {}).get("arguments", {}) or {}
            print(f"[PRODUCTS AGENT] 🔧 Tool {i + 1}: {tool_name}")
            print(f"[PRODUCTS AGENT] 📝 Tool args: {tool_args}")

            if tool_name not in ["stock_monitoring", "price_monitoring"]:
                continue

            bulk_data = tool_args.get("bulkStockMonitoring") or tool_args.get("bulkPriceMonitoring", {})
            # isApplyToAllProducts may appear nested or at the top level of the args.
            is_apply_to_all = bool(
                bulk_data.get("isApplyToAllProducts", tool_args.get("isApplyToAllProducts", False))
            )

            product_ids = tool_args.get("productIds", [])
            if isinstance(product_ids, str) and product_ids.lower() == "all":
                is_apply_to_all = True

            if "all products" in user_message:
                is_apply_to_all = True

            if is_apply_to_all:
                needs_all_products_confirmation = True

        if needs_all_products_confirmation:
            print("[PRODUCTS AGENT] ⚠️ Confirmation required for 'all products' operation")
            confirmation_question = self._build_all_products_confirmation(tool_calls)
            print(f"[PRODUCTS AGENT] 📝 Confirmation question: {confirmation_question}")
            return {
                "toolCallsMade": tool_calls,
                "requiresConfirmation": True,
                "clarificationQuestion": confirmation_question,
                "finalResponse": {"message": confirmation_question, "actionsExecuted": []},
            }

        print("[PRODUCTS AGENT] ✅ Proceeding with tool execution")
        return {"toolCallsMade": tool_calls}

    async def _call_llm_node(self, state: AgentState) -> Dict[str, Any]:
        print("[PRODUCTS AGENT] 🤖 CALL_LLM_NODE")
        user_message = state.get("userMessage", "")
        print(f"[PRODUCTS AGENT] 📝 User message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        
        # If toolCallsMade already exists (from confirmation), skip LLM call
        if state.get("toolCallsMade") and state["toolCallsMade"]:
            print("[PRODUCTS AGENT] 🔧 Tool calls already present in state (from confirmation), skipping LLM")
            return {}  # Don't return toolCallsMade - it's already in state
        
        try:
            print("[PRODUCTS AGENT] 🔄 Calling LLM with tools...")
            # Get the tools to pass to LLM
            tools_to_pass = self._get_langchain_tools()
            print(f"[PRODUCTS AGENT] 🔧 Tools to pass: {len(tools_to_pass)}")
            
            llm_response = await self._call_llm(state, tools_available=True, tools=tools_to_pass)
            
            print("[PRODUCTS AGENT] ✅ LLM response received")
            print(f"[PRODUCTS AGENT] 📦 Response type: {type(llm_response)}")
            
            if isinstance(llm_response, dict):
                if "content" in llm_response:
                    content = llm_response["content"]
                    print(f"[PRODUCTS AGENT] 💬 LLM content: '{content[:150]}{'...' if len(content) > 150 else ''}'")
                
                if "tool_calls" in llm_response and llm_response["tool_calls"]:
                    tool_calls = llm_response["tool_calls"]
                    print(f"[PRODUCTS AGENT] 🔧 Tool calls detected: {len(tool_calls)}")
                    return self._process_tool_calls(state, tool_calls)

                # LLM returned text only — synthesize a tool call for clear monitoring intents
                content = llm_response.get("content", "") if isinstance(llm_response, dict) else ""
                fallback_calls = self._build_monitoring_fallback_tool_call(state)
                if fallback_calls:
                    reason = (
                        "LLM asked for product IDs already in context"
                        if self._llm_asked_for_product_ids(content)
                        else "clear monitoring request without tool call"
                    )
                    print(f"[PRODUCTS AGENT] 🛠️ Overriding text response ({reason})")
                    return self._process_tool_calls(state, fallback_calls)
            
            # No tool calls, just text response
            print("[PRODUCTS AGENT] 💬 No tool calls - text response only")
            return {
                "toolCallsMade": [],
                "finalResponse": {"message": llm_response.get("content", "I understand your request."), "actionsExecuted": []}
            }
            
        except Exception as e:
            error_detail = describe_exception(e)
            logger.exception("Products agent LLM call failed")
            print(f"[PRODUCTS AGENT] ❌ LLM call failed: {error_detail}")
            return {
                "toolCallsMade": [],
                "finalResponse": {"message": f"Products agent error: {error_detail}", "actionsExecuted": []}
            }

    async def _execute_tool_node(self, state: AgentState) -> Dict[str, Any]:
        print("[PRODUCTS AGENT] 🔧 EXECUTE_TOOL_NODE")
        
        try:
            result = await self._execute_tool(state)
            print("[PRODUCTS AGENT] ✅ Tool execution completed")
            print(f"[PRODUCTS AGENT] 📦 Result type: {type(result)}")
            
            if isinstance(result, dict):
                print(f"[PRODUCTS AGENT] 📋 Result keys: {list(result.keys())}")
                # Base agent returns new tool results, accumulate with existing
                if "toolResults" in result:
                    new_results = result["toolResults"]
                    existing_results = state.get("toolResults", [])
                    all_results = existing_results + new_results
                    print(f"[PRODUCTS AGENT] ✅ Accumulated tool results: {len(all_results)} total")
                    return {"toolResults": all_results}
                # Fallback for direct tool result (shouldn't happen)
                if "success" in result:
                    print(f"[PRODUCTS AGENT] ✅ Tool success: {result['success']}")
                if "message" in result:
                    message_content = result['message']
                    if len(message_content) > 100:
                        message_preview = message_content[:100] + "..."
                    else:
                        message_preview = message_content
                    print(f"[PRODUCTS AGENT] 💬 Tool message: '{message_preview}'")
                existing_results = state.get("toolResults", [])
                return {"toolResults": existing_results + [result]}
            
            existing_results = state.get("toolResults", [])
            return {"toolResults": existing_results + [result]}
            
        except Exception as e:
            print(f"[PRODUCTS AGENT] ❌ Tool execution failed: {str(e)}")
            return {"toolResults": [{"success": False, "message": f"Tool execution error: {str(e)}"}]}

    async def _generate_response_node(self, state: AgentState) -> Dict[str, Any]:
        print("[PRODUCTS AGENT] 📝 GENERATE_RESPONSE_NODE")
        
        # If we have tool results, call LLM to generate natural language response
        tool_results = state.get("toolResults", [])
        tool_calls_made = state.get("toolCallsMade", [])
        
        if tool_results and tool_calls_made:
            print(f"[PRODUCTS AGENT] 🔧 Generating response from {len(tool_results)} tool results")
            
            # Build tool results summary for LLM
            tool_summary = []
            actions_executed = []
            
            for i, result in enumerate(tool_results):
                if isinstance(result, dict):
                    # Result might be the actual tool result or wrapped
                    if "tool_name" in result:
                        # Direct tool result from base agent
                        success = result.get("success", False)
                        message = result.get("message", "")
                        tool_name = result.get("tool_name", tool_calls_made[i].get("function", {}).get("name", "unknown") if i < len(tool_calls_made) else "unknown")
                    else:
                        # Fallback
                        success = result.get("success", False)
                        message = result.get("message", "")
                        tool_name = tool_calls_made[i].get("function", {}).get("name", "unknown") if i < len(tool_calls_made) else "unknown"
                    
                    print(f"[PRODUCTS AGENT] 📋 Tool result {i+1}: {tool_name} - success={success}")
                    tool_summary.append(f"{tool_name}: {message}")
                    
                    actions_executed.append({
                        "intent": tool_name.upper(),
                        "success": success,
                        "affectedCount": result.get("affectedCount", 1)
                    })
            
            # Call LLM to generate natural language response
            user_message = state.get("userMessage", "")
            summary_text = "\n".join(tool_summary)
            
            # Get product IDs from context
            product_ids = state.get("userContext", {}).get("selected_product_ids", [])
            
            response_prompt = f"""User request: "{user_message}"

Tool execution results:
{summary_text}

Product IDs affected: {product_ids if product_ids else 'All products'}

Generate a natural language response to the user based on these results. Be concise and helpful. Mention the number of products affected if applicable."""
            
            try:
                llm_response = await self._call_llm(state, tools_available=False, custom_prompt=response_prompt)
                
                if isinstance(llm_response, dict) and "content" in llm_response:
                    final_message = llm_response["content"]
                else:
                    final_message = str(llm_response)
                
                print(f"[PRODUCTS AGENT] ✅ LLM generated response: '{final_message[:100]}{'...' if len(final_message) > 100 else ''}'")
                
                return {
                    "finalResponse": {
                        "message": final_message,
                        "actionsExecuted": actions_executed
                    }
                }
            except Exception as e:
                print(f"[PRODUCTS AGENT] ❌ LLM response generation failed: {str(e)}")
                # Fallback to simple summary
                return {
                    "finalResponse": {
                        "message": f"Successfully completed your request. {summary_text}",
                        "actionsExecuted": actions_executed
                    }
                }
        
        # No tool results, use existing final response or generate default
        if state.get("finalResponse"):
            final_response = state["finalResponse"]
            print("[PRODUCTS AGENT] ✅ Using existing final response")
            
            # If it's the tool decision JSON, replace with a better message
            if isinstance(final_response, dict) and "tool" in final_response:
                return {
                    "finalResponse": {
                        "message": "I've processed your request successfully.",
                        "actionsExecuted": []
                    }
                }
            
            return {"finalResponse": final_response}
        
        print("[PRODUCTS AGENT] 💬 No tool results - generating default response")
        return {
            "finalResponse": {
                "message": "I understand your request.",
                "actionsExecuted": []
            }
        }

    def _decide_next_step(self, state: AgentState) -> str:
        if state.get("toolCallsMade") and state["toolCallsMade"][-1]:
            # If there's a pending confirmation, we short-circuit
            if state.get("requiresConfirmation", False):
                return "final_response"
            return "tool_code"
        if state.get("finalResponse"):
            return "final_response"
        return "clarification"
