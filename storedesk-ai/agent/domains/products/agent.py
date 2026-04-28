from agent.base_agent import BaseAgent, AgentState, HumanMessage, AIMessage, SystemMessage
from agent.domains.products import product_tool_registry
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from config.settings import settings

# Define the system prompt for the Product Agent
PRODUCT_AGENT_SYSTEM_PROMPT = (
    "You help with product management. "
    "Use tools for stock alerts and price monitoring.\n\n"
    "Tools:\n"
    "- stock_monitoring\n"
    "- price_monitoring\n\n"
    "Product IDs: {product_ids}"
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
                    
                    for i, tool_call in enumerate(tool_calls):
                        tool_name = tool_call.get("function", {}).get("name", "unknown")
                        tool_args = tool_call.get("function", {}).get("arguments", {})
                        print(f"[PRODUCTS AGENT] 🔧 Tool {i+1}: {tool_name}")
                        print(f"[PRODUCTS AGENT] 📝 Tool args: {tool_args}")
                        
                        # Check for confirmation requirement
                        if tool_name in ["stock_monitoring", "price_monitoring"]:
                            # Check parsed bulk data
                            bulk_data = tool_args.get("bulkStockMonitoring") or tool_args.get("bulkPriceMonitoring", {})
                            is_apply_to_all = bulk_data.get("isApplyToAllProducts", False)
                            
                            # Also check raw parameters for 'all' string
                            product_ids = tool_args.get("productIds", [])
                            if isinstance(product_ids, str) and product_ids.lower() == "all":
                                is_apply_to_all = True
                            
                            # Check if user message contains "all products" and no specific IDs
                            user_message = state.get("userMessage", "").lower()
                            if "all products" in user_message and not product_ids:
                                is_apply_to_all = True
                            
                            if is_apply_to_all:
                                print("[PRODUCTS AGENT] ⚠️ Confirmation required for 'all products' operation")
                                confirmation_question = f"Are you sure you want to apply this {tool_name.replace('_', ' ')} to all products?"
                                return {
                                    "toolCallsMade": tool_calls,
                                    "requiresConfirmation": True,
                                    "clarificationQuestion": confirmation_question,
                                    "finalResponse": {"message": confirmation_question, "actionsExecuted": []}
                                }
                    
                    # Normal tool execution (no confirmation needed)
                    print("[PRODUCTS AGENT] ✅ Proceeding with tool execution")
                    return {
                        "toolCallsMade": tool_calls
                    }
            
            # No tool calls, just text response
            print("[PRODUCTS AGENT] 💬 No tool calls - text response only")
            return {
                "toolCallsMade": [],
                "finalResponse": {"message": llm_response.get("content", "I understand your request."), "actionsExecuted": []}
            }
            
        except Exception as e:
            print(f"[PRODUCTS AGENT] ❌ LLM call failed: {str(e)}")
            return {
                "toolCallsMade": [],
                "finalResponse": {"message": f"Products agent error: {str(e)}", "actionsExecuted": []}
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
