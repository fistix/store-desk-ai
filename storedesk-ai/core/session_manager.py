import redis.asyncio as redis
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import settings
from .redis_client import redis_client

class SessionManager:
    def __init__(self):
        self.redis_client = redis_client

    async def _get_key(self, session_id: str, key_type: str) -> str:
        return f"session:{session_id}:{key_type}"

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        key = await self._get_key(session_id, "history")
        history_json = await self.redis_client.lrange(key, 0, -1)
        history = [json.loads(item) for item in history_json]
        await self.redis_client.expire(key, settings.SESSION_TTL_SECONDS) # Reset TTL
        return history

    async def add_to_history(self, session_id: str, role: str, content: str):
        key = await self._get_key(session_id, "history")
        message = {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
        await self.redis_client.rpush(key, json.dumps(message))
        await self.redis_client.ltrim(key, -settings.MAX_HISTORY_TURNS, -1) # Hard cap history
        await self.redis_client.expire(key, settings.SESSION_TTL_SECONDS) # Reset TTL

    async def get_pending_confirmation(self, session_id: str) -> Optional[Dict[str, Any]]:
        key = await self._get_key(session_id, "pending_confirmation")
        pending_json = await self.redis_client.get(key)
        if pending_json:
            return json.loads(pending_json)
        return None

    async def set_pending_confirmation(self, session_id: str, intent: str, parameters: Dict[str, Any], confirmation_question: str, user_context: Dict[str, Any]):
        key = await self._get_key(session_id, "pending_confirmation")
        pending_data = {
            "pendingIntent": intent,
            "pendingParameters": parameters,
            "confirmationQuestion": confirmation_question,
            "userContext": user_context,
            "triggeredAt": datetime.utcnow().isoformat()
        }
        await self.redis_client.setex(key, 300, json.dumps(pending_data)) # 5 minute TTL

    async def clear_pending_confirmation(self, session_id: str):
        key = await self._get_key(session_id, "pending_confirmation")
        await self.redis_client.delete(key)

    async def clear_session(self, session_id: str):
        history_key = await self._get_key(session_id, "history")
        pending_key = await self._get_key(session_id, "pending_confirmation")
        await self.redis_client.delete(history_key, pending_key)

session_manager = SessionManager()
