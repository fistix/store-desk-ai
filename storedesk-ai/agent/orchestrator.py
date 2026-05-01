from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from config.settings import settings
from core.session_manager import session_manager
from core.context import UserContext
from agent.base_agent import AgentState
from agent.domains import domain_registry
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .semantic_intent_classifier import SemanticIntentClassifier

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
        self.intent_classifier = SemanticIntentClassifier()
        print("[ORCHESTRATOR] 🚀 INITIALIZING ORCHESTRATOR")
        print("[ORCHESTRATOR] 📋 Loading domain agents...")
        
        self.domains = {name: cls() for name, cls in domain_registry.domains.items()}
        print(f"[ORCHESTRATOR] ✅ Loaded {len(self.domains)} domains: {list(self.domains.keys())}")
        
        print("[ORCHESTRATOR] 🏗️ Building LangGraph...")
        self.graph = self._build_graph()
        print("[ORCHESTRATOR] ✅ Graph built successfully")
        print("[ORCHESTRATOR] 🎯 Orchestrator ready for requests")

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

        # Use ML-based routing decision from _route_to_domain_node
        def route_decision(state):
            routing_decision = state.get("routing_decision", "clarification")
            matched_keywords = state.get("matched_keywords", [])
            intent_confidence = state.get("intent_confidence", 0.0)
            
            print(f"[ORCHESTRATOR] ROUTING DECISION")
            print(f"[ORCHESTRATOR] Message: {state.get('userMessage', '')[:100]}{'...' if len(state.get('userMessage', '')) > 100 else ''}")
            print(f"[ORCHESTRATOR] Matched keywords: {matched_keywords}")
            print(f"[ORCHESTRATOR] Routing decision: {routing_decision}")
            print(f"[ORCHESTRATOR] Intent confidence: {intent_confidence}")
            print(f"[ORCHESTRATOR] Full state keys: {list(state.keys())}")
            
            if routing_decision == "products":
                decision = "run_products_agent"
                print(f"[ORCHESTRATOR] ROUTING TO: {decision} (products agent)")
            else:
                decision = "handle_clarification"
                print(f"[ORCHESTRATOR] ROUTING TO: {decision} (clarification)")
            
            return decision
        
        graph.add_conditional_edges(
            "route_to_domain",
            lambda state: (
                print(f"[ORCHESTRATOR] 🔄 CONDITIONAL EDGE - routing_decision: {state.get('routing_decision')}")
                or ("run_products_agent" if state.get("routing_decision") == "products" else "handle_clarification")
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
                
                # Apply parsing logic to ensure isApplyToAllProducts is set correctly
                parameters = pending_confirmation["pendingParameters"].copy()
                tool_name = pending_confirmation["pendingIntent"]
                
                if tool_name in ["stock_monitoring", "price_monitoring"]:
                    # Check conversation history for "all products" in the original request
                    conversation_history = state.get("conversationHistory", [])
                    original_request = ""
                    # Search entire history for the original request with "all products"
                    for msg in conversation_history:
                        if msg.get("role") == "user" and "all products" in msg.get("content", "").lower():
                            original_request = msg.get("content", "")
                            break
                    
                    print(f"[ORCHESTRATOR] 📝 Original request with 'all products': '{original_request}'")
                    
                    # If original request mentioned "all products", set isApplyToAllProducts to True
                    if original_request:
                        print("[ORCHESTRATOR] ✅ Setting isApplyToAllProducts to True based on original request")
                        if tool_name == "stock_monitoring" and "bulkStockMonitoring" in parameters:
                            parameters["bulkStockMonitoring"]["isApplyToAllProducts"] = True
                        elif tool_name == "price_monitoring" and "bulkPriceMonitoring" in parameters:
                            parameters["bulkPriceMonitoring"]["isApplyToAllProducts"] = True
                
                return {
                    "userMessage": state.get("userMessage", ""),  # Keep original user message
                    "toolCallsMade": [{
                        "function": {
                            "name": tool_name,
                            "arguments": parameters
                        }
                    }],
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
        print(f"[ORCHESTRATOR] 📝 Analyzing message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        
        # Use ML-based intent classification
        intent_result = self.intent_classifier.classify_intent(user_message)
        print(f"[ORCHESTRATOR] 🎯 ML Intent: {intent_result.intent} (confidence: {intent_result.confidence:.2f})")
        print(f"[ORCHESTRATOR] 🔍 Entities: {intent_result.entities}")
        
        # Route based on ML classification with confidence threshold
        if intent_result.intent in ["stock_monitoring", "price_monitoring"] and intent_result.confidence > 0.3:
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
