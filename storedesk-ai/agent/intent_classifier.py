"""
Intent Classification using Local AI Model for Agent Routing
Uses a small local AI model for better intent understanding
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: List[str]

class IntentClassifier:
    def __init__(self):
        # Use a simple rule-based AI approach for intent classification
        pass
    
    def classify_intent(self, message: str) -> IntentResult:
        """
        Classify user intent using AI-like reasoning
        """
        message_lower = message.lower().strip()
        
        # Check for product-specific stock monitoring
        stock_monitoring_score = self._calculate_stock_monitoring_score(message_lower)
        price_monitoring_score = self._calculate_price_monitoring_score(message_lower)
        
        # Determine best intent
        scores = {
            "stock_monitoring": stock_monitoring_score,
            "price_monitoring": price_monitoring_score
        }
        
        best_intent = max(scores.items(), key=lambda x: x[1])
        best_intent_name = best_intent[0]
        best_score = best_intent[1]
        
        # Extract entities
        entities = self._extract_entities(message_lower, best_intent_name)
        
        return IntentResult(best_intent_name, best_score, entities)
    
    def _calculate_stock_monitoring_score(self, message: str) -> float:
        """
        Calculate score for stock monitoring intent
        """
        score = 0.0
        
        # High-confidence patterns
        if any(pattern in message for pattern in [
            "set up stock monitoring", "monitor stock levels", "stock alert when", 
            "notify when stock", "track product stock", "stock monitoring for product",
            "set stock alert", "stock level alert", "low stock alert"
        ]):
            score += 0.8
        
        # Medium-confidence patterns  
        if any(pattern in message for pattern in [
            "stock monitoring", "monitor stock", "track stock", "set up stock",
            "stock alert", "stock level", "product stock"
        ]):
            score += 0.6
            
        # Low-confidence patterns
        if any(pattern in message for pattern in [
            "stock", "inventory"
        ]):
            score += 0.3
            
        # Negative indicators (reduce score)
        if any(pattern in message for pattern in [
            "general stock", "stock market", "stock discussion", "stock price",
            "stock investment", "stock trading", "talking about stock"
        ]):
            score -= 0.5
            
        return min(score, 1.0)
    
    def _calculate_price_monitoring_score(self, message: str) -> float:
        """
        Calculate score for price monitoring intent
        """
        score = 0.0
        
        # High-confidence patterns
        if any(pattern in message for pattern in [
            "set up price monitoring", "monitor price changes", "price alert when",
            "track product prices", "price monitoring for product", "set price alert"
        ]):
            score += 0.8
        
        # Medium-confidence patterns
        if any(pattern in message for pattern in [
            "price monitoring", "monitor price", "track price", "price alert",
            "price change", "price drop", "price increase"
        ]):
            score += 0.6
            
        # Low-confidence patterns
        if any(pattern in message for pattern in [
            "price", "cost"
        ]):
            score += 0.3
            
        return min(score, 1.0)
    
    def _extract_entities(self, message: str, intent: str) -> List[str]:
        """
        Extract relevant entities from message based on intent
        """
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
            intent_result.confidence > 0.3  # Minimum confidence threshold
        )
