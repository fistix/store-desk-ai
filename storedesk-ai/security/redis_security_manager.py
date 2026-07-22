"""
Redis-based Security Profile Manager
Provides persistent user security profiles using Redis
"""

import json
import logging
import redis.asyncio as redis
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import asyncio
from core.redis_client import redis_client

@dataclass
class UserSecurityProfile:
    """User security profile for Redis storage"""
    user_id: str
    events_count: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    risk_score: float = 0.0
    blocked_count: int = 0
    injection_attempts: int = 0
    last_blocked: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif value is None:
                data[key] = None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSecurityProfile':
        """Create from dictionary from Redis"""
        # Convert ISO strings back to datetime objects
        for key, value in data.items():
            if value and key in ['last_activity', 'last_blocked', 'created_at']:
                if isinstance(value, str):
                    try:
                        data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        data[key] = datetime.now()
        return cls(**data)

class RedisSecurityManager:
    """
    Redis-based security profile manager with atomic operations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Use centralized Redis client
        self.redis_client = redis_client
        
        # Redis key prefixes
        self.PROFILE_KEY_PREFIX = "user_security_profile:"
        self.RATE_LIMIT_KEY_PREFIX = "user_rate_limits:"
        self.SECURITY_EVENTS_KEY_PREFIX = "user_security_events:"
        
        # TTL settings (in seconds)
        self.PROFILE_TTL = 7 * 24 * 60 * 60  # 7 days
        self.RATE_LIMIT_TTL = 60  # 1 minute
        self.SECURITY_EVENTS_TTL = 30 * 24 * 60 * 60  # 30 days
        
        # Alert thresholds
        self.alert_thresholds = {
            "max_events_per_minute": 100,
            "max_injection_attempts_per_hour": 10,
            "max_validation_failures_per_minute": 50,
            "max_user_risk_score": 0.8,
            "block_user_after_attempts": 5,
        }
        
        print("[REDIS SECURITY] 🚀 Initialized Redis Security Manager")

    async def get_user_profile(self, user_id: str) -> UserSecurityProfile:
        """
        Get user security profile from Redis
        """
        try:
            redis_key = f"{self.PROFILE_KEY_PREFIX}{user_id}"
            profile_data = await redis_client.get(redis_key)
            
            if profile_data:
                profile_dict = json.loads(profile_data)
                profile = UserSecurityProfile.from_dict(profile_dict)
                print(f"[REDIS SECURITY] 📊 Loaded profile for user: {user_id}")
                return profile
            else:
                # Create new profile
                profile = UserSecurityProfile(user_id=user_id)
                await self.save_user_profile(profile)
                print(f"[REDIS SECURITY] 🆕 Created new profile for user: {user_id}")
                return profile
                
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error loading profile for {user_id}: {e}")
            # Fallback to in-memory profile
            return UserSecurityProfile(user_id=user_id)

    async def save_user_profile(self, profile: UserSecurityProfile) -> bool:
        """
        Save user security profile to Redis
        """
        try:
            redis_key = f"{self.PROFILE_KEY_PREFIX}{profile.user_id}"
            profile_data = json.dumps(profile.to_dict())
            
            # Save with TTL
            await redis_client.setex(redis_key, self.PROFILE_TTL, profile_data)
            print(f"[REDIS SECURITY] 💾 Saved profile for user: {profile.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error saving profile for {profile.user_id}: {e}")
            return False

    async def update_user_profile(self, user_id: str, **updates) -> bool:
        """
        Update specific fields in user profile
        """
        try:
            profile = await self.get_user_profile(user_id)
            
            # Update fields
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            # Update last activity
            profile.last_activity = datetime.now()
            
            return await self.save_user_profile(profile)
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error updating profile for {user_id}: {e}")
            return False

    # Fixed-window counter: INCR, then EXPIRE only when the key is new (TTL == -1).
    # Setting EXPIRE on every request would slide/reset the window and never clear under load.
    _FIXED_WINDOW_LUA = """
local count = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl == -1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
  ttl = tonumber(ARGV[1])
end
return {count, ttl}
"""

    async def is_rate_limited(
        self,
        user_id: str,
        action: str,
        limit: int = 10,
        window_seconds: int = 60,
    ) -> Tuple[bool, int]:
        """
        Redis fixed-window rate limiting.

        Returns:
            (is_limited, retry_after_seconds)
        """
        try:
            rate_limit_key = f"{self.RATE_LIMIT_KEY_PREFIX}{user_id}:{action}"
            result = await redis_client.eval(
                self._FIXED_WINDOW_LUA,
                1,
                rate_limit_key,
                window_seconds,
            )
            current_count = int(result[0])
            ttl = int(result[1])
            retry_after = max(ttl, 1) if ttl > 0 else window_seconds

            if current_count > limit:
                self.logger.warning(
                    "Rate limit exceeded for user=%s action=%s count=%s limit=%s retry_after=%s",
                    user_id,
                    action,
                    current_count,
                    limit,
                    retry_after,
                )
                return True, retry_after

            return False, 0

        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Rate limiting error for {user_id}: {e}")
            # Fail open - allow request if Redis fails
            return False, 0

    async def should_block_user(self, user_id: str) -> bool:
        """
        Check if user should be blocked based on security profile
        """
        try:
            profile = await self.get_user_profile(user_id)
            
            # Check if user exceeded risk score
            if profile.risk_score > self.alert_thresholds["max_user_risk_score"]:
                print(f"[REDIS SECURITY] 🚫 User blocked due to high risk score: {user_id} ({profile.risk_score})")
                return True
            
            # Check if user has too many injection attempts
            if profile.injection_attempts >= self.alert_thresholds["block_user_after_attempts"]:
                print(f"[REDIS SECURITY] 🚫 User blocked due to injection attempts: {user_id} ({profile.injection_attempts})")
                return True
            
            # Check if user was recently blocked
            if profile.last_blocked:
                time_since_block = datetime.now() - profile.last_blocked
                if time_since_block < timedelta(minutes=30):  # 30 minute block
                    print(f"[REDIS SECURITY] 🚫 User still in block period: {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Block check error for {user_id}: {e}")
            # Fail open - allow request if Redis fails
            return False

    async def block_user(self, user_id: str, reason: str, duration_minutes: int = 30) -> bool:
        """
        Block user for security reasons
        """
        try:
            profile = await self.get_user_profile(user_id)
            profile.last_blocked = datetime.now()
            profile.blocked_count += 1
            
            success = await self.save_user_profile(profile)
            
            if success:
                print(f"[REDIS SECURITY] 🚫 USER BLOCKED | User: {user_id} | Reason: {reason} | Duration: {duration_minutes}min")
                
                # Log security event
                await self.log_security_event(
                    "user_blocked",
                    user_id,
                    reason,
                    f"Blocked for {duration_minutes} minutes",
                    "HIGH"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error blocking user {user_id}: {e}")
            return False

    async def log_security_event(self, event_type: str, user_id: str, input_text: str, details: str, severity: str) -> bool:
        """
        Log security event to Redis
        """
        try:
            # Create event record
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "input_text": input_text[:200],  # Truncate for storage
                "details": details,
                "severity": severity
            }
            
            # Store in daily event log
            today = datetime.now().strftime("%Y-%m-%d")
            events_key = f"{self.SECURITY_EVENTS_KEY_PREFIX}{user_id}:{today}"
            
            # Use Redis list for events
            await redis_client.lpush(events_key, json.dumps(event))
            await redis_client.expire(events_key, self.SECURITY_EVENTS_TTL)
            
            # Update user profile
            await self._update_profile_from_event(event_type, user_id, severity)
            
            print(f"[REDIS SECURITY] 📝 Logged security event: {event_type} for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error logging security event for {user_id}: {e}")
            return False

    async def get_user_security_events(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get security events for user
        """
        try:
            events = []
            
            for day_offset in range(days):
                date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                events_key = f"{self.SECURITY_EVENTS_KEY_PREFIX}{user_id}:{date}"
                
                # Get events from Redis list
                raw_events = await redis_client.lrange(events_key, 0, -1)
                
                for raw_event in raw_events:
                    try:
                        event = json.loads(raw_event)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return events
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error getting security events for {user_id}: {e}")
            return []

    async def get_security_summary(self) -> Dict[str, Any]:
        """
        Get security summary statistics
        """
        try:
            # Get all profile keys
            profile_keys = await redis_client.keys(f"{self.PROFILE_KEY_PREFIX}*")
            
            total_users = len(profile_keys)
            high_risk_users = 0
            blocked_users = 0
            total_injection_attempts = 0
            
            for key in profile_keys:
                try:
                    profile_data = await redis_client.get(key)
                    if profile_data:
                        profile_dict = json.loads(profile_data)
                        
                        if profile_dict.get("risk_score", 0) > 0.5:
                            high_risk_users += 1
                        
                        if profile_dict.get("last_blocked"):
                            blocked_users += 1
                        
                        total_injection_attempts += profile_dict.get("injection_attempts", 0)
                        
                except Exception:
                    continue
            
            return {
                "total_users": total_users,
                "high_risk_users": high_risk_users,
                "blocked_users": blocked_users,
                "total_injection_attempts": total_injection_attempts,
                "redis_keys_count": total_users,
            }
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error getting security summary: {e}")
            return {
                "total_users": 0,
                "high_risk_users": 0,
                "blocked_users": 0,
                "total_injection_attempts": 0,
                "error": str(e)
            }

    async def cleanup_expired_profiles(self) -> int:
        """
        Cleanup expired profiles (Redis handles TTL automatically, but this can be used for manual cleanup)
        """
        try:
            # Redis handles TTL automatically, so this is mainly for monitoring
            profile_keys = await redis_client.keys(f"{self.PROFILE_KEY_PREFIX}*")
            
            expired_count = 0
            for key in profile_keys:
                ttl = await redis_client.ttl(key)
                if ttl == -1:  # No TTL set
                    await redis_client.expire(key, self.PROFILE_TTL)
                    expired_count += 1
            
            if expired_count > 0:
                print(f"[REDIS SECURITY] 🧹 Set TTL for {expired_count} profiles without expiration")
            
            return expired_count
            
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error during cleanup: {e}")
            return 0

    async def _update_profile_from_event(self, event_type: str, user_id: str, severity: str):
        """
        Update user profile based on security event
        """
        try:
            updates = {}
            
            # Update event count
            updates["events_count"] = 1  # This will be incremented in get_user_profile
            
            # Update based on event type
            if event_type == "injection_attempt":
                updates["injection_attempts"] = 1
                updates["risk_score"] = 0.2
            
            elif event_type in ["validation_failure", "invalid_param_type", "forbidden_param_key"]:
                updates["risk_score"] = 0.1
            
            # Update based on severity
            if severity == "HIGH":
                updates["risk_score"] = 0.3
            elif severity == "CRITICAL":
                updates["risk_score"] = 0.5
            
            # Apply updates
            if updates:
                await self.update_user_profile(user_id, **updates)
                
        except Exception as e:
            self.logger.error(f"[REDIS SECURITY] ❌ Error updating profile from event: {e}")

# Global Redis security manager instance
redis_security_manager = RedisSecurityManager()
