import os
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
import json

from config.settings import settings
from providers.base import LLMProvider
from providers.gemini import GeminiProvider
from providers.openai import OpenAIProvider
from fastapi import HTTPException
import time

class ProviderManager:
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self._load_simple_providers()

    def _load_simple_providers(self):
        """Simplified provider loading - only Gemini and OpenAI"""
        print("[PROVIDER_MANAGER] Starting simplified provider loading...")
        
        # Load Gemini if API key is available
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key:
            print("[PROVIDER_MANAGER] Loading Gemini provider...")
            self.providers.append(GeminiProvider("gemini", "gemini-3-flash-preview", gemini_key))
            print("[PROVIDER_MANAGER] ✅ Gemini provider loaded successfully")
        else:
            print("[PROVIDER_MANAGER] ⚠️ Gemini API key not found, skipping Gemini")
        
        # Load OpenAI if API key is available
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            print("[PROVIDER_MANAGER] Loading OpenAI provider...")
            self.providers.append(OpenAIProvider("openai", "gpt-4o-mini", openai_key))
            print("[PROVIDER_MANAGER] ✅ OpenAI provider loaded successfully")
        else:
            print("[PROVIDER_MANAGER] ⚠️ OpenAI API key not found, skipping OpenAI")
        
        print(f"[PROVIDER_MANAGER] Total providers loaded: {len(self.providers)}")
        for provider in self.providers:
            print(f"[PROVIDER_MANAGER] - {provider.name} ({provider.model})")

    async def _get_usage_key(self, provider_name: str) -> str:
        # Usage key can be daily, or other resets based on config
        today_utc = datetime.utcnow().strftime("%Y-%m-%d")
        return f"provider_usage:{provider_name}:{today_utc}"

    async def _get_status_key(self, provider_name: str) -> str:
        return f"provider_status:{provider_name}"

    async def get_provider_status(self, provider_name: str) -> Dict[str, Any]:
        status_key = await self._get_status_key(provider_name)
        status_json = await self.redis_client.get(status_key)
        if status_json:
            return json.loads(status_json)
        return {"status": "active", "until": None}

    async def set_provider_backoff(self, provider_name: str, seconds: int):
        status_key = await self._get_status_key(provider_name)
        status_data = {"status": "backoff", "until": (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()}
        await self.redis_client.setex(status_key, seconds, json.dumps(status_data))

    async def increment_usage(self, provider_name: str):
        usage_key = await self._get_usage_key(provider_name)
        await self.redis_client.incr(usage_key)
        # Set/reset TTL for usage key to expire at midnight UTC if applicable
        # This logic would be more complex for other reset types
        # For simplicity, assuming daily reset for now
        if "midnight_utc" in (p["reset"] for p in yaml.safe_load(open(os.path.join(os.path.dirname(__file__), '..' ,'config', 'providers.yaml'))).get("providers",[])): # Check if reset type is midnight_utc
             now = datetime.utcnow()
             midnight = now.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(microseconds=1)
             await self.redis_client.expireat(usage_key, int(midnight.timestamp()))

    async def get_current_usage(self, provider_name: str) -> int:
        usage_key = await self._get_usage_key(provider_name)
        usage = await self.redis_client.get(usage_key)
        return int(usage) if usage else 0

    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        print(f"[PROVIDER_MANAGER] 🚀 Starting LLM completion request")
        print(f"[PROVIDER_MANAGER] 📊 Available providers: {len(self.providers)}")
        print(f"[PROVIDER_MANAGER] 📝 Messages to process: {len(messages)}")
        print(f"[PROVIDER_MANAGER] 🔧 Tools available: {len(tools) if tools else 0}")
        
        # Log message details
        for i, msg in enumerate(messages):
            print(f"[PROVIDER_MANAGER] 📨 Message {i+1} type: {type(msg)}")
            if hasattr(msg, 'role'):
                role = msg.role
            elif hasattr(msg, 'type'):
                # LangChain messages use 'type' attribute instead of 'role'
                if msg.type == 'system':
                    role = 'system'
                elif msg.type == 'human':
                    role = 'user'  
                elif msg.type == 'ai':
                    role = 'assistant'
                else:
                    role = 'unknown'
            else:
                role = msg.get('role', 'unknown')
            
            if hasattr(msg, 'content'):
                content = msg.content
            else:
                content = msg.get('content', '')
            
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"[PROVIDER_MANAGER] 📨 Message {i+1} ({role}): {content_preview}")
            
            if i < 5:  # Show first few messages in detail
                print(f"[PROVIDER_MANAGER] 🔍 Message {i+1} details: {msg}")
        
        # Try each provider in order
        for i, provider in enumerate(self.providers):
            print(f"[PROVIDER_MANAGER] 🔄 Attempting provider {i+1}/{len(self.providers)}: {provider.name} ({provider.model})")
            
            try:
                start_time = time.time()
                print(f"[PROVIDER_MANAGER] ⏱️ Calling {provider.name} API...")
                
                response = await provider.complete(messages, tools)
                
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                print(f"[PROVIDER_MANAGER] ✅ {provider.name} responded in {duration_ms:.2f}ms")
                print(f"[PROVIDER_MANAGER] 📦 Response type: {type(response)}")
                
                # Log response details
                if isinstance(response, dict):
                    if 'content' in response:
                        content = response['content']
                        content_preview = content[:150] + "..." if len(content) > 150 else content
                        print(f"[PROVIDER_MANAGER] 💬 Response content: {content_preview}")
                    
                    if 'tool_calls' in response and response['tool_calls']:
                        tool_calls = response['tool_calls']
                        print(f"[PROVIDER_MANAGER] 🔧 Tool calls detected: {len(tool_calls)}")
                        for j, tool_call in enumerate(tool_calls):
                            tool_name = tool_call.get('function', {}).get('name', 'unknown')
                            print(f"[PROVIDER_MANAGER] 🔧 Tool {j+1}: {tool_name}")
                
                # Add provider info to response
                response["activeProvider"] = provider.name
                response["providerDuration"] = duration_ms
                
                print(f"[PROVIDER_MANAGER] 🎉 SUCCESS: Used {provider.name} provider")
                return response
                
                # Add provider info to response
                response["activeProvider"] = provider.name
                response["providerDuration"] = duration_ms
                
                print(f"[PROVIDER_MANAGER] 🎉 SUCCESS: Used {provider.name} provider")
                return response
                
            except Exception as e:
                print(f"[PROVIDER_MANAGER] ❌ {provider.name} failed: {str(e)}")
                print(f"[PROVIDER_MANAGER] 🔄 Trying next provider...")
                continue
        
        # All providers failed
        print(f"[PROVIDER_MANAGER] 💥 CRITICAL: All {len(self.providers)} providers failed")
        raise HTTPException(status_code=503, detail="All LLM providers are currently unavailable or exhausted.")

provider_manager = ProviderManager()
