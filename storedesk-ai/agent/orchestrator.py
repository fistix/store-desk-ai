import os
import logging
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from config.settings import settings
from core.session_manager import session_manager
from core.context import UserContext
from agent.base_agent import AgentState
from agent.domains import domain_registry
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .semantic_intent_classifier import SemanticIntentClassifier
from .llm_intent_classifier import LLMIntentClassifier
from security.prompt_sanitizer import PromptSanitizer, SecurityException
from security.security_monitor import security_monitor

logger = logging.getLogger(__name__)

# Define the orchestrator system prompt
ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are the central AI orchestrator for StoreDesk, a dropshipping agency platform. "
    "Your role is to understand user commands in natural language, identify the relevant domain, "
    "and delegate to specialized agents. If a user command relates to product management "
    "(like stock or price monitoring), route to the 'products' agent. "
    "If a user asks for clarification or you need more information, generate a clarification question. "
    "Manage the conversation flow, including handling pending confirmations."
)

class Orchestrator:
    def __init__(self):
        self.domains = domain_registry
        
        # Initialize security components
        self.prompt_sanitizer = PromptSanitizer()
        
        # Initialize intent classifier based on configuration
        use_llm_routing = os.getenv("USE_LLM_FOR_AGENT_ROUTING", "false").lower() == "true"
        provider_priority = os.getenv("LLM_ROUTING_PROVIDER_PRIORITY", "gemini,openai")
        
        if use_llm_routing:
            self.intent_classifier = LLMIntentClassifier(use_llm_routing=True, provider_priority=provider_priority)
        else:
            self.intent_classifier = SemanticIntentClassifier()
        
        self.domains = {name: cls() for name, cls in domain_registry.domains.items()}
        self.graph = self._build_graph()
        logger.info(
            "Orchestrator ready with domains=%s router=%s",
            list(self.domains.keys()),
            type(self.intent_classifier).__name__,
        )

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("resolve_confirmation", self._resolve_confirmation_node)
        graph.add_node("route_to_domain", self._route_to_domain_node)
        graph.add_node("handle_clarification", self._handle_clarification_node)
        graph.add_node("compose_response", self._compose_response_node)
        graph.add_node("run_products_agent", self._run_products_agent_node)

        graph.set_entry_point("resolve_confirmation")

        graph.add_conditional_edges(
            "resolve_confirmation",
            self._decide_after_confirmation,
            {
                "proceed_with_action": "run_products_agent",
                "clarification": "handle_clarification",
                "cancel": "compose_response",
                "no_pending": "route_to_domain"
            }
        )

        graph.add_conditional_edges(
            "route_to_domain",
            lambda state: (
                "run_products_agent"
                if state.get("routing_decision") == "products"
                else "handle_clarification"
            ),
            {
                "run_products_agent": "run_products_agent",
                "handle_clarification": "handle_clarification"
            }
        )
        
        graph.add_edge("run_products_agent", "compose_response")
        graph.add_edge("handle_clarification", "compose_response")
        graph.add_edge("compose_response", END)
        return graph

    async def _resolve_confirmation_node(self, state: AgentState) -> Dict[str, Any]:
        print("[ORCHESTRATOR] 🔍 RESOLVE_CONFIRMATION_NODE")
        print(f"[ORCHESTRATOR] 📝 User message: '{state.get('userMessage', '')}'")
        
        pending_confirmation = state.get("pendingConfirmation")
        user_message = state["userMessage"].lower()
        
        print(f"[ORCHESTRATOR] 🔄 Pending confirmation: {bool(pending_confirmation)}")
        
        if pending_confirmation:
            print("[ORCHESTRATOR] ⚠️ Pending confirmation found, checking user response...")
            
            # Check for affirmative messages
            if any(keyword in user_message for keyword in ["yes", "confirm", "proceed", "ok", "sure", "do it"]):
                print("[ORCHESTRATOR] ✅ User confirmed - proceeding with stored action")

                # Restore every stored tool call (supports multi-tool actions like
                # disabling both stock and price monitoring). Fall back to the legacy
                # single-intent fields for confirmations stored before this change.
                pending_tool_calls = pending_confirmation.get("pendingToolCalls")
                if not pending_tool_calls:
                    pending_tool_calls = [{
                        "function": {
                            "name": pending_confirmation["pendingIntent"],
                            "arguments": pending_confirmation["pendingParameters"],
                        }
                    }]

                # Determine whether the original request targeted all products.
                conversation_history = state.get("conversationHistory", [])
                original_request = ""
                for msg in conversation_history:
                    if msg.get("role") == "user" and "all products" in msg.get("content", "").lower():
                        original_request = msg.get("content", "")
                        break
                print(f"[ORCHESTRATOR] 📝 Original request with 'all products': '{original_request}'")

                restored_tool_calls = []
                for tool_call in pending_tool_calls:
                    function = tool_call.get("function", {})
                    tool_name = function.get("name")
                    arguments = dict(function.get("arguments", {}) or {})

                    if original_request and tool_name in ["stock_monitoring", "price_monitoring"]:
                        print(f"[ORCHESTRATOR] ✅ Setting isApplyToAllProducts to True for {tool_name}")
                        if tool_name == "stock_monitoring" and "bulkStockMonitoring" in arguments:
                            arguments["bulkStockMonitoring"] = {
                                **arguments["bulkStockMonitoring"],
                                "isApplyToAllProducts": True,
                            }
                        elif tool_name == "price_monitoring" and "bulkPriceMonitoring" in arguments:
                            arguments["bulkPriceMonitoring"] = {
                                **arguments["bulkPriceMonitoring"],
                                "isApplyToAllProducts": True,
                            }

                    restored_tool_calls.append({
                        "function": {"name": tool_name, "arguments": arguments}
                    })

                print(f"[ORCHESTRATOR] 🔧 Restoring {len(restored_tool_calls)} tool call(s) from confirmation")

                return {
                    "userMessage": state.get("userMessage", ""),  # Keep original user message
                    "toolCallsMade": restored_tool_calls,
                    "userContext": pending_confirmation["userContext"],
                    "pendingConfirmation": None,
                    "requiresConfirmation": False
                }
            
            # Check for negative messages
            elif any(keyword in user_message for keyword in ["no", "cancel", "stop", "nevermind", "don't"]):
                print("[ORCHESTRATOR] ❌ User cancelled - stopping action")
                return {"finalResponse": {"message": "Action cancelled.", "actionsExecuted": []}, "pendingConfirmation": None}
            
            else:
                print("[ORCHESTRATOR] ❓ Unclear response - asking for clarification")
                return {
                    "finalResponse": {
                        "message": f"You have a pending action: {pending_confirmation['confirmationQuestion']}. Please confirm or cancel.", 
                        "actionsExecuted": []
                    }, 
                    "clarificationQuestion": pending_confirmation["confirmationQuestion"]
                }
        else:
            print("[ORCHESTRATOR] ✅ No pending confirmation - proceeding to routing")
            return {"route_decision": "no_pending"}
    
    def _decide_after_confirmation(self, state: AgentState) -> str:
        if state.get("finalResponse") and "Action cancelled." in state["finalResponse"]["message"]:
            return "cancel"
        if state.get("clarificationQuestion"):
            return "clarification"
        if state.get("toolCallsMade") and state["toolCallsMade"][-1]: # If confirmation led to a tool call
            return "proceed_with_action"
        return "no_pending"

    async def _route_to_domain_node(self, state: AgentState) -> Dict[str, Any]:
        print("[ORCHESTRATOR] 🧭 ROUTE_TO_DOMAIN_NODE")
        user_message = state.get("userMessage", "")
        user_id = state.get("userContext", {}).get("user_id", "unknown")
        print(f"[ORCHESTRATOR] 📝 Analyzing message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        
        # Additional security validation at orchestrator level
        try:
            # Validate message content again
            if self.prompt_sanitizer.detect_injection(user_message, user_id):
                await security_monitor.log_security_event(
                    "orchestrator_injection_detected",
                    user_id,
                    user_message[:100],
                    "Injection detected at orchestrator level",
                    "HIGH"
                )
                # Route to clarification for suspicious input
                return {
                    **state,
                    "routing_decision": "clarification",
                    "matched_keywords": [],
                    "intent_confidence": 0.0,
                    "security_flag": True
                }
            
            # Sanitize conversation history
            conversation_history = state.get("conversationHistory", [])
            if conversation_history:
                sanitized_history = self.prompt_sanitizer.sanitize_message_history(conversation_history, user_id)
                state["conversationHistory"] = sanitized_history
                
        except Exception as e:
            print(f"[ORCHESTRATOR] ❌ Security validation error: {e}")
            await security_monitor.log_security_event(
                "orchestrator_security_error",
                user_id,
                str(e),
                "Security validation failed",
                "MEDIUM"
            )
        
        # Use ML-based intent classification (pass recent history for follow-ups)
        intent_result = await self.intent_classifier.classify_intent(
            user_message, state.get("conversationHistory", [])
        )
        print(f"[ORCHESTRATOR] 🎯 ML Intent: {intent_result.intent} (confidence: {intent_result.confidence:.2f})")
        print(f"[ORCHESTRATOR] 🔍 Entities: {intent_result.entities}")
        
        # Route based on ML classification with confidence threshold
        if intent_result.intent in ["all_monitoring", "stock_monitoring", "price_monitoring"] and intent_result.confidence > 0.3:
            print("[ORCHESTRATOR] ✅ Routing to PRODUCTS domain")
            result_state = {
                **state,  # Merge existing state
                "routing_decision": "products", 
                "matched_keywords": [intent_result.intent], 
                "intent_confidence": intent_result.confidence
            }
            print(f"[ORCHESTRATOR] 🔄 Returning state with keys: {list(result_state.keys())}")
            print(f"[ORCHESTRATOR] 🔄 routing_decision in returned state: {result_state.get('routing_decision')}")
            print(f"[ORCHESTRATOR] 🔄 intent_confidence in returned state: {result_state.get('intent_confidence')}")
            return result_state
        else:
            print(f"[ORCHESTRATOR] ❓ Low confidence ({intent_result.confidence:.2f}) or wrong intent - routing to clarification")
            result_state = {
                **state,  # Merge existing state
                "routing_decision": "clarification", 
                "matched_keywords": [], 
                "intent_confidence": intent_result.confidence
            }
            print(f"[ORCHESTRATOR] 🔄 Returning state with keys: {list(result_state.keys())}")
            print(f"[ORCHESTRATOR] 🔄 routing_decision in returned state: {result_state.get('routing_decision')}")
            print(f"[ORCHESTRATOR] 🔄 intent_confidence in returned state: {result_state.get('intent_confidence')}")
            return result_state
    
    async def _run_products_agent_node(self, state: AgentState) -> Dict[str, Any]:
        print("[ORCHESTRATOR] 🏭 RUN_PRODUCTS_AGENT_NODE")
        print(f"[ORCHESTRATOR] 📊 Available domains: {list(self.domains.keys())}")
        
        products_agent = self.domains.get("products")
        if not products_agent:
            print("[ORCHESTRATOR] ❌ ERROR: Products agent not found!")
            return {"finalResponse": {"message": "Products agent not available", "actionsExecuted": []}}
        
        print("[ORCHESTRATOR] ✅ Products agent found - invoking...")
        print(f"[ORCHESTRATOR] 📝 State keys: {list(state.keys())}")
        print(f"[ORCHESTRATOR] 📝 User message: {state.get('userMessage', '')[:100]}{'...' if len(state.get('userMessage', '')) > 100 else ''}")
        
        # Log toolCallsMade before invoking
        if state.get("toolCallsMade"):
            print(f"[ORCHESTRATOR] 🔧 Tool calls BEFORE agent: {len(state['toolCallsMade'])}")
            for i, tc in enumerate(state["toolCallsMade"]):
                print(f"[ORCHESTRATOR] 🔧   Tool {i+1}: {tc.get('function', {}).get('name', 'unknown')}")
        
        try:
            result = await products_agent.invoke(state)
            print("[ORCHESTRATOR] ✅ Products agent completed successfully")
            print(f"[ORCHESTRATOR] 📦 Result type: {type(result)}")
            print(f"[ORCHESTRATOR] 📋 Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Log key result fields
            if isinstance(result, dict):
                if "toolCallsMade" in result:
                    tool_calls = result["toolCallsMade"]
                    print(f"[ORCHESTRATOR] 🔧 Tool calls AFTER agent: {len(tool_calls)}")
                    for i, tool_call in enumerate(tool_calls):
                        tool_name = tool_call.get("function", {}).get("name", "unknown")
                        print(f"[ORCHESTRATOR] 🔧 Tool {i+1}: {tool_name}")
                
                if "finalResponse" in result:
                    response = result["finalResponse"]
                    print(f"[ORCHESTRATOR] 💬 Final response: {response.get('message', '')[:100]}{'...' if len(response.get('message', '')) > 100 else ''}")
            
            return result
            
        except Exception as e:
            print(f"[ORCHESTRATOR] ❌ Products agent failed: {str(e)}")
            return {"finalResponse": {"message": f"Products agent error: {str(e)}", "actionsExecuted": []}}

    async def _handle_clarification_node(self, state: AgentState) -> Dict[str, Any]:
        # This node would typically generate a clarification question.
        # For now, it reuses the clarificationQuestion set by other nodes.
        return {"finalResponse": {"message": state.get("clarificationQuestion", "I couldn't understand your request. Can you please rephrase?"), "actionsExecuted": []}}

    async def _compose_response_node(self, state: AgentState) -> Dict[str, Any]:
        # If the state already has a finalResponse (e.g., from cancellation or direct LLM response)
        if state.get("finalResponse"):
            return state["finalResponse"]
        
        # Otherwise, compose a response from tool results
        response_message = ""
        actions_executed = state.get("actionsExecuted", [])

        if state.get("toolResults"):
            for res in state["toolResults"]:
                response_message += f"""
- {res.get("message", "")}"""
                actions_executed.append({
                    "intent": res["tool_name"].replace("_tool", "").upper(),
                    "success": res["success"],
                    "affectedCount": res.get("affectedCount", 0)
                })
        
        final_response_message = response_message or "I have processed your request."

        return {
            "success": True,
            "message": final_response_message.strip(),
            "actionsExecuted": actions_executed,
            "requiresConfirmation": state.get("requiresConfirmation", False),
            "confirmationQuestion": state.get("clarificationQuestion") if state.get("requiresConfirmation") else None,
            "clarificationQuestion": state.get("clarificationQuestion") if not state.get("requiresConfirmation") else None,
            "activeProvider": state.get("activeProvider", "unknown")
        }

orchestrator = Orchestrator()
