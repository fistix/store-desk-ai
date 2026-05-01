"""
Semantic Intent Classification using Embeddings
Fast, accurate routing using cosine similarity between embeddings
"""

import re
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: List[str]
    matched_example: str

class SemanticIntentClassifier:
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model = embedding_model
        self.embeddings_cache = {}
        self.route_examples = {
            "stock_monitoring": [
                "set up stock monitoring for products",
                "monitor stock levels",
                "create stock alerts when low",
                "track inventory levels",
                "notify when stock is low",
                "set stock alert threshold",
                "check inventory status",
                "monitor product stock",
                "set up low stock alerts",
                "track stock quantities",
                "enable quantity monitoring",
                "quantity monitoring for products",
                "monitor quantity levels",
                "set quantity alert threshold",
                "enable stock monitoring",
                "turn on quantity monitoring",
                "quantity monitoring with threshold",
                "monitor product quantities",
                "track quantity levels",
                "set up quantity alerts",
                "enable inventory monitoring",
                "quantity tracking for products",
                "monitor stock quantities",
                "set quantity threshold",
                "enable stock level monitoring"
            ],
            "price_monitoring": [
                "set up price monitoring",
                "monitor price changes",
                "create price alerts",
                "track product prices",
                "notify when price drops",
                "set price threshold alerts",
                "monitor price fluctuations",
                "track pricing trends",
                "set up price change notifications",
                "monitor competitor pricing",
                "enable price monitoring",
                "price monitoring for products",
                "monitor price levels",
                "set price alert threshold",
                "enable price tracking",
                "price monitoring with threshold",
                "track product pricing",
                "set up price alerts",
                "enable margin monitoring",
                "price margin monitoring",
                "monitor price changes",
                "set price percentage threshold"
            ],
            "general_chat": [
                "hello",
                "how are you",
                "what can you do",
                "help me",
                "tell me about your features",
                "general conversation",
                "chat with me",
                "explain how this works"
            ]
        }
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embedding model and pre-compute route embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"[SEMANTIC CLASSIFIER] 🤖 Loading embedding model: {self.embedding_model}")
            self.model = SentenceTransformer(self.embedding_model)
            
            # Pre-compute embeddings for route examples
            print("[SEMANTIC CLASSIFIER] 📊 Computing route embeddings...")
            for intent, examples in self.route_examples.items():
                embeddings = self.model.encode(examples, convert_to_tensor=True)
                self.embeddings_cache[intent] = {
                    'embeddings': embeddings,
                    'examples': examples
                }
            
            print("[SEMANTIC CLASSIFIER] ✅ Embeddings computed and cached")
            
        except ImportError:
            print("[SEMANTIC CLASSIFIER] ❌ sentence-transformers not installed, falling back to rule-based")
            self.model = None
        except Exception as e:
            print(f"[SEMANTIC CLASSIFIER] ❌ Failed to load embedding model: {e}")
            self.model = None
    
    def _compute_cosine_similarity(self, query_embedding: np.ndarray, route_embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and route embeddings"""
        # Normalize embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        route_norms = route_embeddings / np.linalg.norm(route_embeddings, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarities = np.dot(route_norms, query_norm.T)
        return similarities
    
    def classify_intent(self, message: str) -> IntentResult:
        """
        Classify intent using semantic similarity
        """
        if self.model is None:
            return self._fallback_classification(message)
        
        try:
            # Pre-process message
            message_clean = self._preprocess_message(message)
            
            # Compute embedding for user message
            query_embedding = self.model.encode([message_clean], convert_to_tensor=True)
            query_embedding = query_embedding.cpu().numpy()
            
            # Compute similarity with each route
            best_intent = None
            best_confidence = 0.0
            best_example = ""
            
            for intent, cache_data in self.embeddings_cache.items():
                route_embeddings = cache_data['embeddings'].cpu().numpy()
                examples = cache_data['examples']
                
                # Compute similarities
                similarities = self._compute_cosine_similarity(query_embedding[0], route_embeddings)
                max_similarity = np.max(similarities)
                
                if max_similarity > best_confidence:
                    best_confidence = max_similarity
                    best_intent = intent
                    best_example = examples[np.argmax(similarities)]
            
            # Extract entities
            entities = self._extract_entities(message, best_intent or "general_chat")
            
            return IntentResult(
                intent=best_intent or "general_chat",
                confidence=float(best_confidence),
                entities=entities,
                matched_example=best_example
            )
            
        except Exception as e:
            print(f"[SEMANTIC CLASSIFIER] ❌ Semantic classification failed: {e}")
            return self._fallback_classification(message)
    
    def _preprocess_message(self, message: str) -> str:
        """Pre-process message for better embedding matching"""
        # Convert to lowercase
        message = message.lower().strip()
        
        # Remove extra whitespace
        message = re.sub(r'\s+', ' ', message)
        
        # Remove special characters but keep important ones
        message = re.sub(r'[^\w\s\-\.\%]', '', message)
        
        return message
    
    def _fallback_classification(self, message: str) -> IntentResult:
        """
        Fallback rule-based classification
        """
        message_lower = message.lower()
        
        # Enhanced keyword matching with context
        stock_keywords = [
            "stock monitoring", "stock alert", "monitor stock", "track stock",
            "inventory alert", "low stock", "stock level", "set up stock",
            "product stock", "stock quantities", "check inventory",
            "quantity monitoring", "quantity alert", "monitor quantity",
            "track quantity", "quantity level", "quantity threshold",
            "enable stock", "enable quantity", "turn on stock", "turn on quantity"
        ]
        
        price_keywords = [
            "price monitoring", "price alert", "monitor price", "track price",
            "price change", "price drop", "price threshold", "set up price",
            "price fluctuations", "pricing trends", "price margin",
            "margin monitoring", "price percentage", "price level"
        ]
        
        # Check stock monitoring
        stock_score = sum(1 for kw in stock_keywords if kw in message_lower)
        if stock_score >= 2:
            return IntentResult("stock_monitoring", 0.7, [], "Rule-based: multiple stock keywords")
        elif stock_score == 1:
            # Check if it's about product stock (not general stock discussion)
            product_context = any(ctx in message_lower for ctx in ["product", "inventory", "level", "alert", "monitor"])
            if product_context:
                return IntentResult("stock_monitoring", 0.6, [], "Rule-based: product stock context")
        
        # Check price monitoring
        price_score = sum(1 for kw in price_keywords if kw in message_lower)
        if price_score >= 2:
            return IntentResult("price_monitoring", 0.7, [], "Rule-based: multiple price keywords")
        elif price_score == 1:
            product_context = any(ctx in message_lower for ctx in ["product", "alert", "monitor", "track"])
            if product_context:
                return IntentResult("price_monitoring", 0.6, [], "Rule-based: product price context")
        
        # Default to general chat
        return IntentResult("general_chat", 0.4, [], "Rule-based: no clear intent")
    
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
            intent_result.intent in ["stock_monitoring", "price_monitoring"] and
            intent_result.confidence > 0.3  # Minimum confidence threshold
        )
    
    def add_route_examples(self, intent: str, examples: List[str]):
        """
        Add new examples for a route (dynamic learning)
        """
        if intent not in self.route_examples:
            self.route_examples[intent] = []
        
        self.route_examples[intent].extend(examples)
        
        # Re-compute embeddings if model is available
        if self.model is not None:
            embeddings = self.model.encode(examples, convert_to_tensor=True)
            if intent in self.embeddings_cache:
                self.embeddings_cache[intent]['embeddings'] = torch.cat([
                    self.embeddings_cache[intent]['embeddings'],
                    embeddings
                ])
                self.embeddings_cache[intent]['examples'].extend(examples)
            else:
                self.embeddings_cache[intent] = {
                    'embeddings': embeddings,
                    'examples': examples
                }
