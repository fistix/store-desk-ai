import asyncio
import redis.asyncio as redis
from config.settings import settings

async def clear_test_session_history():
    """Clear accumulated history for test session"""
    redis_client = redis.from_url(settings.REDIS_URL)
    
    # Clear test session history
    await redis_client.delete("session:test-session-123:history")
    await redis_client.delete("session:test-session-123:confirmation")
    
    print("Cleared test session history")
    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(clear_test_session_history())
