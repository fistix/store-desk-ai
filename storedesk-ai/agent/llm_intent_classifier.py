"""
LLM-based Intent Classification for Agent Routing
Uses external LLM providers for intelligent intent understanding
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: List[str]
    reasoning: str
    matched_example: str = ""

class LLMIntentClassifier:
    def __init__(self, use_llm_routing: bool = True, provider_priority: str = "gemini,openai,groq"):
        self.use_llm_routing = use_llm_routing
        self.provider_priority = [p.strip() for p in provider_priority.split(",") if p.strip()]
        self.provider_manager = None
        self.semantic_classifier = None
        
        # Initialize providers
        self._initialize_providers()
        
        # Initialize semantic classifier as fallback
        self._initialize_semantic_classifier()
    
    def _initialize_providers(self):
        """Reuse the shared provider manager for intent classification."""
        try:
            from providers.manager import provider_manager
            self.provider_manager = provider_manager
            print(f"[LLM INTENT CLASSIFIER] ✅ Using shared provider manager")
            print(f"[LLM INTENT CLASSIFIER] 📊 Available providers: {len(self.provider_manager.providers)}")
        except Exception as e:
            print(f"[LLM INTENT CLASSIFIER] ❌ Failed to initialize providers: {e}")
            self.provider_manager = None
    
    def _initialize_semantic_classifier(self):
        """Initialize semantic classifier as fallback"""
        try:
            from .semantic_intent_classifier import SemanticIntentClassifier
            self.semantic_classifier = SemanticIntentClassifier()
            print(f"[LLM INTENT CLASSIFIER] ✅ Semantic classifier initialized as fallback")
        except Exception as e:
            print(f"[LLM INTENT CLASSIFIER] ❌ Failed to initialize semantic classifier: {e}")
            self.semantic_classifier = None
    
    async def classify_intent(self, message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> IntentResult:
        """
        Classify user intent using LLM providers with fallback chain
        """
        print(f"[LLM INTENT CLASSIFIER] 🎯 Classifying intent: '{message[:50]}...'")
        
        # Check if LLM routing is enabled
        if not self.use_llm_routing:
            print(f"[LLM INTENT CLASSIFIER] 📊 LLM routing disabled, using semantic classifier")
            return await self._classify_with_semantic(message)
        
        # Try LLM providers first
        if self.provider_manager and self.provider_manager.providers:
            return await self._classify_with_llm(message, conversation_history)
        
        # Fallback to semantic classifier
        print(f"[LLM INTENT CLASSIFIER] 📊 No providers available, using semantic classifier")
        return await self._classify_with_semantic(message)

    def _format_recent_context(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """Render the last few turns so follow-up replies can be understood in context."""
        if not conversation_history:
            return ""
        recent = conversation_history[-4:]
        lines = []
        for turn in recent:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
        if not lines:
            return ""
        return "Recent conversation (for context):\n" + "\n".join(lines) + "\n\n"

    async def _classify_with_llm(self, message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> IntentResult:
        """
        Classify intent using LLM providers
        """
        context_block = self._format_recent_context(conversation_history)
        prompt = f"""You are an intent classifier for a product management system.

{context_block}The latest user message is what you must classify. Use the recent conversation only to resolve short follow-ups (e.g. "selected products only", "yes", "the second one").

Classify this user message into exactly one of these intents:
1. "all_monitoring" - The user wants to enable, disable, or configure monitoring in general, or BOTH stock and price monitoring together (e.g. "all monitoring", "both monitoring", "stock and price monitoring", or an unqualified "monitoring" that does not specify stock or price).
2. "stock_monitoring" - The user wants to enable, disable, turn on/off, change, or configure ONLY stock / quantity / inventory monitoring or alerts.
3. "price_monitoring" - The user wants to enable, disable, turn on/off, change, or configure ONLY price monitoring or alerts.
4. "general_chat" - Anything else that is not about configuring product stock or price monitoring.

Important rules:
- Both ENABLING and DISABLING monitoring are valid monitoring intents (do NOT classify a disable request as general_chat).
- Prefer "all_monitoring" whenever the user says "all monitoring", "both monitoring", mentions stock and price together, OR says just "monitoring" without specifying stock or price (e.g. "disable monitoring for selected products").
- Use "stock_monitoring" or "price_monitoring" only when the request clearly names stock/quantity or price specifically.
- Any request to enable/disable/turn on/turn off "monitoring" for products is a monitoring intent, never general_chat.

User message: "{message}"

Return JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

JSON:"""

        try:
            # The provider manager handles priority ordering and failover across
            # the configured providers (see ProviderManager.complete).
            messages = [{"role": "user", "content": prompt}]
            response = await self.provider_manager.complete(messages)

            if response and response.get("content"):
                content = response["content"]
                provider_name = response.get("activeProvider", "llm")
                print(f"[LLM INTENT CLASSIFIER] 📝 {provider_name} response: {content[:100]}...")

                parsed_result = self._parse_llm_response(content, message)
                if parsed_result:
                    print(f"[LLM INTENT CLASSIFIER] ✅ {provider_name} classified: {parsed_result.intent} (confidence: {parsed_result.confidence:.2f})")
                    return parsed_result
                print(f"[LLM INTENT CLASSIFIER] ❌ {provider_name} failed to parse response")

            # LLM returned nothing usable, fallback to semantic
            print(f"[LLM INTENT CLASSIFIER] 📊 LLM returned no usable response, using semantic classifier")
            return await self._classify_with_semantic(message)

        except Exception as e:
            print(f"[LLM INTENT CLASSIFIER] ❌ LLM classification failed: {e!r}, using semantic classifier")
            return await self._classify_with_semantic(message)
    
    def _parse_llm_response(self, content: str, message: str) -> Optional[IntentResult]:
        """
        Parse LLM response into IntentResult
        """
        try:
            # Extract JSON from response
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                
                result = json.loads(json_str)
                
                # Validate intent
                intent = result.get("intent", "general_chat")
                if intent not in ["all_monitoring", "stock_monitoring", "price_monitoring", "general_chat"]:
                    intent = "general_chat"
                
                # Extract entities
                entities = self._extract_entities(message, intent)
                
                return IntentResult(
                    intent=intent,
                    confidence=float(result.get("confidence", 0.5)),
                    entities=entities,
                    reasoning=result.get("reasoning", ""),
                    matched_example=""
                )
            else:
                return None
                
        except Exception as e:
            print(f"[LLM INTENT CLASSIFIER] ❌ Failed to parse response: {e}")
            return None
    
    async def _classify_with_semantic(self, message: str) -> IntentResult:
        """
        Classify intent using semantic classifier
        """
        if self.semantic_classifier:
            try:
                result = await self.semantic_classifier.classify_intent(message)
                print(f"[LLM INTENT CLASSIFIER] 📊 Semantic classified: {result.intent} (confidence: {result.confidence:.2f})")
                return result
            except Exception as e:
                print(f"[LLM INTENT CLASSIFIER] ❌ Semantic classification failed: {e}")
        
        # Final fallback to rule-based
        print(f"[LLM INTENT CLASSIFIER] 📊 Using rule-based fallback")
        return self._fallback_classification(message)
    
    def _fallback_classification(self, message: str) -> IntentResult:
        """
        Fallback rule-based classification
        """
        message_lower = message.lower()
        
        # Simple keyword-based fallback
        if any(kw in message_lower for kw in ["all monitoring", "both monitoring", "stock and price", "price and stock"]):
            return IntentResult("all_monitoring", 0.7, [], "Rule-based fallback")
        if any(kw in message_lower for kw in ["stock monitoring", "stock alert", "monitor stock", "quantity monitoring"]):
            return IntentResult("stock_monitoring", 0.6, [], "Rule-based fallback")
        elif any(kw in message_lower for kw in ["price monitoring", "price alert", "monitor price"]):
            return IntentResult("price_monitoring", 0.6, [], "Rule-based fallback")
        elif "monitoring" in message_lower or "monitor" in message_lower:
            # Unqualified monitoring request -> treat as both stock and price.
            return IntentResult("all_monitoring", 0.6, [], "Rule-based fallback")
        else:
            return IntentResult("general_chat", 0.4, [], "Rule-based fallback")
    
    def _extract_entities(self, message: str, intent: str) -> List[str]:
        """
        Extract relevant entities from message based on intent
        """
        import re
        entities = []
        
        if intent == "stock_monitoring":
            # Extract numbers for thresholds
            numbers = re.findall(r'\d+', message)
            entities.extend([f"threshold_{num}" for num in numbers])
            
        elif intent == "price_monitoring":
            # Extract percentages and numbers
            percentages = re.findall(r'\d+%', message)
            numbers = re.findall(r'\d+', message)
            entities.extend([f"percentage_{p.rstrip('%')}" for p in percentages])
            entities.extend([f"threshold_{num}" for num in numbers])
        
        return entities
    
    def should_route_to_products(self, intent_result: IntentResult) -> bool:
        """
        Determine if intent should route to products domain
        """
        return (
            intent_result.intent in ["all_monitoring", "stock_monitoring", "price_monitoring"] and
            intent_result.confidence > 0.3
        )
