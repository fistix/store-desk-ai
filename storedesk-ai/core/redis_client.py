"""
Redis Client Module
Centralized Redis client for all Redis operations
"""

import redis.asyncio as redis
from config.settings import settings

# Global Redis client instance - shared across all modules
redis_client = redis.from_url(settings.REDIS_URL)

async def get_redis_client():
    """Get Redis client instance"""
    return redis_client

async def test_redis_connection():
    """Test Redis connection"""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        print(f"[REDIS CLIENT] ❌ Connection failed: {e}")
        return False
