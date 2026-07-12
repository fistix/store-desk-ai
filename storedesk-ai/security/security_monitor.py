"""
Security Monitoring and Alerting System
Provides comprehensive security event monitoring and anomaly detection
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from .redis_security_manager import redis_security_manager

@dataclass
class SecurityMetrics:
    """Security metrics tracking"""
    total_events: int = 0
    injection_attempts: int = 0
    validation_failures: int = 0
    blocked_requests: int = 0
    high_severity_events: int = 0
    critical_events: int = 0

@dataclass
class UserSecurityProfile:
    """User-specific security profile"""
    user_id: str
    events_count: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    risk_score: float = 0.0
    blocked_count: int = 0
    injection_attempts: int = 0
    last_blocked: Optional[datetime] = None

class SecurityMonitor:
    """
    Comprehensive security monitoring and alerting system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.lock = Lock()
        
        # Event tracking (keep for in-memory fallback)
        self.events = deque(maxlen=10000)  # Keep last 10,000 events
        self.metrics = SecurityMetrics()
        
        # Redis security manager
        self.redis_manager = redis_security_manager
        
        # Alert thresholds
        self.alert_thresholds = {
            "max_events_per_minute": 100,
            "max_injection_attempts_per_hour": 10,
            "max_validation_failures_per_minute": 50,
            "max_user_risk_score": 0.8,
            "block_user_after_attempts": 5,
        }
        
        print("[SECURITY] 🔍 SecurityMonitor initialized with Redis backend")

    async def log_security_event(self, event_type: str, user_id: Optional[str], input_text: str, details: str, severity: str):
        """
        Log and analyze security event using Redis
        """
        with self.lock:
            timestamp = datetime.now()
            
            # Create event record
            event = {
                "timestamp": timestamp,
                "event_type": event_type,
                "user_id": user_id,
                "input_text": input_text[:200],  # Truncate for storage
                "details": details,
                "severity": severity
            }
            
            # Store event in memory (fallback)
            self.events.append(event)
            
            # Update metrics
            self.metrics.total_events += 1
            
            if event_type == "injection_attempt":
                self.metrics.injection_attempts += 1
            elif event_type in ["validation_failure", "invalid_param_type", "forbidden_param_key"]:
                self.metrics.validation_failures += 1
            
            if severity == "HIGH":
                self.metrics.high_severity_events += 1
            elif severity == "CRITICAL":
                self.metrics.critical_events += 1
            
            # Log to Redis (primary storage)
            try:
                await self.redis_manager.log_security_event(event_type, user_id, input_text, details, severity)
            except Exception as e:
                self.logger.error(f"[SECURITY] ❌ Redis logging failed: {e}")
                # Continue with in-memory fallback
            
            # Check for alerts
            self._check_alert_conditions(event)
            
            # Log event
            self.logger.warning(
                f"[SECURITY] 🚨 {event_type} | User: {user_id} | Severity: {severity} | Details: {details}"
            )

    async def should_block_user(self, user_id: str) -> bool:
        """
        Check if user should be blocked based on Redis security profile
        """
        if not user_id:
            return False
        
        try:
            return await self.redis_manager.should_block_user(user_id)
        except Exception as e:
            self.logger.error(f"[SECURITY] ❌ Error checking block status for {user_id}: {e}")
            # Fail open - allow request if Redis fails
            return False

    async def block_user(self, user_id: str, reason: str, duration_minutes: int = 30):
        """
        Block user for security reasons using Redis
        """
        try:
            success = await self.redis_manager.block_user(user_id, reason, duration_minutes)
            if success:
                self.logger.critical(
                    f"[SECURITY] 🚫 USER BLOCKED | User: {user_id} | Reason: {reason} | Duration: {duration_minutes}min"
                )
            return success
        except Exception as e:
            self.logger.error(f"[SECURITY] ❌ Error blocking user {user_id}: {e}")
            return False

    async def is_rate_limited(self, user_id: str, action: str, limit: int = 10, window_minutes: int = 1) -> bool:
        """
        Check if user action is rate limited using Redis
        """
        try:
            return await self.redis_manager.is_rate_limited(user_id, action, limit, window_minutes * 60)
        except Exception as e:
            self.logger.error(f"[SECURITY] ❌ Rate limiting error for {user_id}: {e}")
            # Fail open - allow request if Redis fails
            return False

    async def get_security_summary(self) -> Dict[str, Any]:
        """
        Get security summary statistics from Redis
        """
        try:
            redis_summary = await self.redis_manager.get_security_summary()
            
            return {
                "metrics": {
                    "total_events": self.metrics.total_events,
                    "injection_attempts": self.metrics.injection_attempts,
                    "validation_failures": self.metrics.validation_failures,
                    "blocked_requests": self.metrics.blocked_requests,
                    "high_severity_events": self.metrics.high_severity_events,
                    "critical_events": self.metrics.critical_events,
                },
                "redis_data": redis_summary,
            }
        except Exception as e:
            self.logger.error(f"[SECURITY] ❌ Error getting security summary: {e}")
            return {
                "metrics": {
                    "total_events": self.metrics.total_events,
                    "injection_attempts": self.metrics.injection_attempts,
                    "validation_failures": self.metrics.validation_failures,
                    "blocked_requests": self.metrics.blocked_requests,
                    "high_severity_events": self.metrics.high_severity_events,
                    "critical_events": self.metrics.critical_events,
                },
                "error": str(e)
            }

    async def get_user_security_profile(self, user_id: str) -> Optional[UserSecurityProfile]:
        """
        Get user security profile from Redis
        """
        try:
            return await self.redis_manager.get_user_profile(user_id)
        except Exception as e:
            self.logger.error(f"[SECURITY] ❌ Error getting user profile {user_id}: {e}")
            return None

    def get_recent_events(self, minutes: int = 60, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent security events
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_events = []
        for event in self.events:
            if event["timestamp"] >= cutoff_time:
                if severity is None or event["severity"] == severity:
                    recent_events.append(event)
        
        return recent_events

    def _check_alert_conditions(self, event: Dict[str, Any]):
        """
        Check if event triggers security alerts
        """
        event_type = event["event_type"]
        user_id = event["user_id"]
        severity = event["severity"]
        
        # Check for high-frequency events
        recent_events = self.get_recent_events(minutes=1)
        if len(recent_events) > self.alert_thresholds["max_events_per_minute"]:
            self._trigger_alert("high_event_frequency", f"Events per minute: {len(recent_events)}")
        
        # Check for injection attempt frequency
        injection_events = [e for e in recent_events if e["event_type"] == "injection_attempt"]
        if len(injection_events) > 5:
            self._trigger_alert("high_injection_frequency", f"Injection attempts per minute: {len(injection_events)}")
        
        # Check for user-specific alerts
        if user_id:
            profile = self.user_profiles[user_id]
            
            # High risk score
            if profile.risk_score > 0.8:
                self._trigger_alert("high_user_risk", f"User {user_id} risk score: {profile.risk_score:.2f}")
            
            # Multiple injection attempts
            if profile.injection_attempts >= 3:
                self._trigger_alert("repeated_injection_attempts", f"User {user_id} injection attempts: {profile.injection_attempts}")
        
        # Check for critical events
        if severity == "CRITICAL":
            self._trigger_alert("critical_security_event", f"Critical event: {event_type}")

    def _trigger_alert(self, alert_type: str, details: str):
        """
        Trigger security alert
        """
        self.logger.critical(
            f"[SECURITY] 🚨 ALERT | Type: {alert_type} | Details: {details}"
        )
        
        # In production, this would send alerts to monitoring systems
        # For now, just log the alert

# Global security monitor instance
security_monitor = SecurityMonitor()
