"""
LLM-based Intent Classification for Agent Routing
Uses local small language model for intelligent intent understanding
"""

import os
import json
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: List[str]
    reasoning: str

class LLMIntentClassifier:
    def __init__(self, model_name: str = "tinyllama-1.1b"):
        self.model_name = model_name
        self.model_path = None
        self.llm = None
        self.model_configs = {
            "tinyllama-1.1b": {
                "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                "size": "470MB",
                "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
            },
            "qwen-0.5b": {
                "url": "https://huggingface.co/Qwen/Qwen1.5-0.5B-Chat-GGUF/resolve/main/qwen1.5-0.5b-chat-q4_k_m.gguf",
                "size": "380MB",
                "filename": "qwen1.5-0.5b-chat-q4_k_m.gguf"
            },
            "pythia-160m": {
                "url": "https://huggingface.co/TheBloke/Pythia-160M-SFT-v0.1-GGUF/resolve/main/pythia-160m-sft-v0.1.Q4_K_M.gguf",
                "size": "120MB",
                "filename": "pythia-160m-sft-v0.1.Q4_K_M.gguf"
            }
        }
        self._initialize_model()
    
    def _get_model_dir(self) -> Path:
        """Get or create model directory"""
        model_dir = Path.home() / ".cache" / "intent_models"
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir
    
    def _download_model(self, model_config: Dict) -> Path:
        """Download model if not exists"""
        model_dir = self._get_model_dir()
        model_path = model_dir / model_config["filename"]
        
        if not model_path.exists():
            print(f"[INTENT CLASSIFIER] 📥 Downloading {self.model_name} model ({model_config['size']})...")
            
            # Download with progress
            response = requests.get(model_config["url"], stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(model_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r[INTENT CLASSIFIER] 📥 Downloading... {progress:.1f}%", end="")
            
            print(f"\n[INTENT CLASSIFIER] ✅ Model downloaded to {model_path}")
        else:
            print(f"[INTENT CLASSIFIER] ✅ Model found at {model_path}")
        
        return model_path
    
    def _initialize_model(self):
        """Initialize LLM model"""
        try:
            from llama_cpp import Llama
            
            model_config = self.model_configs.get(self.model_name)
            if not model_config:
                raise ValueError(f"Unknown model: {self.model_name}")
            
            self.model_path = self._download_model(model_config)
            
            print(f"[INTENT CLASSIFIER] 🤖 Loading {self.model_name} model...")
            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=512,
                n_threads=4,
                verbose=False
            )
            print(f"[INTENT CLASSIFIER] ✅ Model loaded successfully")
            
        except ImportError:
            print("[INTENT CLASSIFIER] ❌ llama-cpp-python not installed, falling back to rule-based")
            self.llm = None
        except Exception as e:
            print(f"[INTENT CLASSIFIER] ❌ Failed to load model: {e}")
            self.llm = None
    
    def classify_intent(self, message: str) -> IntentResult:
        """
        Classify user intent using local LLM
        """
        if self.llm is None:
            # Fallback to simple rule-based classification
            return self._fallback_classification(message)
        
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
            response = self.llm(prompt, max_tokens=150, stop=["}"])
            response_text = response["choices"][0]["text"].strip()
            
            # Parse JSON response
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                
                result = json.loads(json_str)
                
                # Extract entities
                entities = self._extract_entities(message, result["intent"])
                
                return IntentResult(
                    intent=result["intent"],
                    confidence=float(result["confidence"]),
                    entities=entities,
                    reasoning=result.get("reasoning", "")
                )
            else:
                return self._fallback_classification(message)
                
        except Exception as e:
            print(f"[INTENT CLASSIFIER] ❌ LLM classification failed: {e}")
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
