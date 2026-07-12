"""
LLM-based Intent Classification for Agent Routing
Uses external LLM providers for intelligent intent understanding
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from providers.manager import ProviderManager

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
        """Initialize LLM providers for intent classification"""
        try:
            self.provider_manager = ProviderManager()
            print(f"[LLM INTENT CLASSIFIER] � Initialized provider manager")
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
    
    async def classify_intent(self, message: str) -> IntentResult:
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
            return await self._classify_with_llm(message)
        
        # Fallback to semantic classifier
        print(f"[LLM INTENT CLASSIFIER] 📊 No providers available, using semantic classifier")
        return await self._classify_with_semantic(message)
    
    async def _classify_with_llm(self, message: str) -> IntentResult:
        """
        Classify intent using LLM providers
        """
        prompt = f"""You are an intent classifier for a product management system. 

Classify this user message into one of these intents:
1. "stock_monitoring" - User wants to set up stock alerts/monitoring for products
2. "price_monitoring" - User wants to set up price alerts/monitoring for products  
3. "general_chat" - General conversation, not about monitoring

User message: "{message}"

Return JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

JSON:"""

        try:
            # Try providers in priority order
            for provider_name in self.provider_priority:
                if provider_name in self.provider_manager.providers:
                    provider = self.provider_manager.providers[provider_name]
                    print(f"[LLM INTENT CLASSIFIER] 🤖 Trying provider: {provider_name}")
                    
                    # Call LLM without tools
                    messages = [{"role": "user", "content": prompt}]
                    response = await provider.complete(messages)
                    
                    if response and "content" in response:
                        content = response["content"]
                        print(f"[LLM INTENT CLASSIFIER] 📝 {provider_name} response: {content[:100]}...")
                        
                        # Parse JSON response
                        parsed_result = self._parse_llm_response(content, message)
                        if parsed_result:
                            print(f"[LLM INTENT CLASSIFIER] ✅ {provider_name} classified: {parsed_result.intent} (confidence: {parsed_result.confidence:.2f})")
                            return parsed_result
                        else:
                            print(f"[LLM INTENT CLASSIFIER] ❌ {provider_name} failed to parse response")
                    else:
                        print(f"[LLM INTENT CLASSIFIER] ❌ {provider_name} no response")
            
            # All providers failed, fallback to semantic
            print(f"[LLM INTENT CLASSIFIER] 📊 All LLM providers failed, using semantic classifier")
            return await self._classify_with_semantic(message)
            
        except Exception as e:
            print(f"[LLM INTENT CLASSIFIER] ❌ LLM classification failed: {e}")
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
                if intent not in ["stock_monitoring", "price_monitoring", "general_chat"]:
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
        if any(kw in message_lower for kw in ["stock monitoring", "stock alert", "monitor stock"]):
            return IntentResult("stock_monitoring", 0.6, [], "Rule-based fallback")
        elif any(kw in message_lower for kw in ["price monitoring", "price alert", "monitor price"]):
            return IntentResult("price_monitoring", 0.6, [], "Rule-based fallback")
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
            intent_result.intent in ["stock_monitoring", "price_monitoring"] and
            intent_result.confidence > 0.3
        )
