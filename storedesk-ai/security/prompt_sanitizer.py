"""
Prompt Injection Security Framework
Provides comprehensive input sanitization and validation for LLM interactions
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SecurityEvent:
    event_type: str
    user_id: Optional[str]
    input_text: str
    pattern_matched: str
    timestamp: datetime
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL

class PromptSanitizer:
    """
    Comprehensive prompt sanitization and validation system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Injection patterns to detect
        self.injection_patterns = [
            # System prompt override attempts
            r"ignore\s+previous\s+instructions",
            r"disregard\s+system\s+prompt", 
            r"override\s+.*\s+prompt",
            r"system\s+prompt\s+ignore",
            r"forget\s+everything\s+above",
            r"ignore\s+all\s+previous",
            r"system\s+message\s+ignore",
            
            # JSON manipulation attempts
            r"\}\s*\{",  # Multiple JSON objects
            r"\\[\"'\\\\]",  # Escape sequences
            r"\]\s*\[",  # Multiple arrays
            r",\s*}",  # Trailing comma
            
            # Command injection attempts
            r"exec\s*\(",
            r"eval\s*\(",
            r"__import__",
            r"subprocess\.",
            r"os\.system",
            r"open\s*\(",
            
            # Context manipulation
            r"conversation\s+history",
            r"previous\s+messages",
            r"system\s+role",
            r"assistant\s+role",
            r"user\s+role",
            
            # Prompt template manipulation
            r"\{\{.*\}\}",  # Template syntax
            r"%.*%",  # String formatting
            r"\$.*\{",  # Variable substitution
            
            # Exfiltration attempts
            r"print\s+.*password",
            r"reveal\s+.*secret",
            r"show\s+.*key",
            r"dump\s+.*data",
            
            # Privilege escalation
            r"admin\s+access",
            r"root\s+privileges",
            r"sudo\s+",
            r"escalate\s+privileges",
        ]
        
        # Validation rules
        self.validation_rules = {
            "max_message_length": 10000,
            "allowed_json_keys": [
                "tool", "parameters", "productIds", "enabled", "threshold", "percentage",
                "type", "bulkStockMonitoring", "bulkPriceMonitoring", "isApplyToAllProducts"
            ],
            "forbidden_patterns": self.injection_patterns,
            "required_structure": ["tool", "parameters"],
            "max_json_depth": 5,
        }
        
        # Compile regex patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
        
        print("[SECURITY] 🛡️ PromptSanitizer initialized")

    def sanitize_input(self, input_text: str, user_id: Optional[str] = None) -> str:
        """
        Sanitize user input to prevent prompt injection
        """
        if not input_text:
            return input_text
            
        original_length = len(input_text)
        
        # Check for injection attempts
        if self.detect_injection(input_text, user_id):
            raise SecurityException("Input contains potentially malicious content")
        
        # Apply sanitization rules
        sanitized = self._apply_sanitization_rules(input_text)
        
        # Validate length
        if len(sanitized) > self.validation_rules["max_message_length"]:
            self._log_security_event(
                "input_too_long", 
                user_id, 
                input_text[:100], 
                f"Length: {len(sanitized)}",
                "MEDIUM"
            )
            raise SecurityException("Input exceeds maximum allowed length")
        
        # Log if content was changed
        if len(sanitized) != original_length:
            self._log_security_event(
                "input_sanitized",
                user_id,
                input_text[:100],
                f"Original: {original_length}, Sanitized: {len(sanitized)}",
                "LOW"
            )
        
        return sanitized

    def detect_injection(self, input_text: str, user_id: Optional[str] = None) -> bool:
        """
        Detect potential injection attempts in input
        """
        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.findall(input_text)
            if matches:
                self._log_security_event(
                    "injection_attempt",
                    user_id,
                    input_text[:100],
                    f"Pattern {i+1}: {pattern.pattern}",
                    "HIGH"
                )
                return True
        
        return False

    def validate_tool_parameters(self, params: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """
        Validate tool parameters for security
        """
        try:
            # Check for required structure
            if not isinstance(params, dict):
                self._log_security_event(
                    "invalid_param_type",
                    user_id,
                    str(params)[:100],
                    "Parameters must be a dictionary",
                    "MEDIUM"
                )
                return False
            
            # Validate parameter keys (be more permissive for legitimate tool calls)
            for key in params.keys():
                if key not in self.validation_rules["allowed_json_keys"]:
                    # Log warning but don't block for potentially valid keys
                    self._log_security_event(
                        "forbidden_param_key",
                        user_id,
                        key,
                        f"Key not in allowed list: {key}",
                        "LOW"  # Reduced severity
                    )
                    # Continue validation instead of immediately failing
                    continue
            
            # Validate nested parameters
            if "parameters" in params:
                nested_params = params["parameters"]
                if not self._validate_nested_parameters(nested_params, user_id):
                    return False
            
            # Validate product IDs if present
            if "productIds" in params:
                if not self._validate_product_ids(params["productIds"], user_id):
                    return False
            
            return True
            
        except Exception as e:
            self._log_security_event(
                "param_validation_error",
                user_id,
                str(params)[:100],
                f"Error: {str(e)}",
                "MEDIUM"
            )
            return False

    def validate_llm_response(self, response: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and sanitize LLM response
        """
        try:
            # Validate response structure
            if not isinstance(response, dict):
                raise SecurityException("Response must be a dictionary")
            
            # Sanitize content
            if "content" in response:
                response["content"] = self.sanitize_input(response["content"], user_id)
            
            # Validate tool calls
            if "tool_calls" in response:
                sanitized_tool_calls = []
                for tool_call in response["tool_calls"]:
                    if self.validate_tool_parameters(tool_call.get("function", {}).get("arguments", {}), user_id):
                        sanitized_tool_calls.append(tool_call)
                    else:
                        self._log_security_event(
                            "invalid_tool_call",
                            user_id,
                            str(tool_call)[:100],
                            "Tool call validation failed",
                            "HIGH"
                        )
                response["tool_calls"] = sanitized_tool_calls
            
            return response
            
        except Exception as e:
            self._log_security_event(
                "response_validation_error",
                user_id,
                str(response)[:100],
                f"Error: {str(e)}",
                "HIGH"
            )
            raise SecurityException(f"Response validation failed: {str(e)}")

    def sanitize_message_history(self, history: List[Dict[str, Any]], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Sanitize conversation history
        """
        sanitized_history = []
        
        for message in history:
            try:
                sanitized_message = message.copy()
                
                # Sanitize message content
                if "content" in sanitized_message:
                    sanitized_message["content"] = self.sanitize_input(sanitized_message["content"], user_id)
                
                # Validate message structure
                if not self._validate_message_structure(sanitized_message, user_id):
                    self._log_security_event(
                        "invalid_message_structure",
                        user_id,
                        str(message)[:100],
                        "Message structure validation failed",
                        "MEDIUM"
                    )
                    continue
                
                sanitized_history.append(sanitized_message)
                
            except Exception as e:
                self._log_security_event(
                    "history_sanitization_error",
                    user_id,
                    str(message)[:100],
                    f"Error: {str(e)}",
                    "MEDIUM"
                )
                continue
        
        return sanitized_history

    def _apply_sanitization_rules(self, text: str) -> str:
        """
        Apply basic sanitization rules to text
        """
        # Remove potentially dangerous escape sequences
        text = re.sub(r'\\[\"\'\\]', '', text)
        
        # Remove multiple JSON objects
        text = re.sub(r'\}\s*\{', '}', text)
        
        # Remove trailing commas in JSON
        text = re.sub(r',\s*}', '}', text)
        
        # Normalize whitespace (but preserve meaningful content)
        text = ' '.join(text.split())
        
        return text

    def _validate_nested_parameters(self, params: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """
        Validate nested parameter structure
        """
        try:
            # Check JSON depth
            json_str = json.dumps(params)
            if self._get_json_depth(json_str) > self.validation_rules["max_json_depth"]:
                self._log_security_event(
                    "json_depth_exceeded",
                    user_id,
                    json_str[:100],
                    f"Depth exceeded: {self._get_json_depth(json_str)}",
                    "MEDIUM"
                )
                return False
            
            # Validate nested structure
            for key, value in params.items():
                if isinstance(value, dict):
                    if not self._validate_nested_parameters(value, user_id):
                        return False
                elif isinstance(value, str):
                    # Only check for injection in string values, not all values
                    if self.detect_injection(value, user_id):
                        return False
            
            return True
            
        except Exception as e:
            self._log_security_event(
                "nested_validation_error",
                user_id,
                str(params)[:100],
                f"Error: {str(e)}",
                "MEDIUM"
            )
            return False

    def _validate_product_ids(self, product_ids: Union[List[str], List[int]], user_id: Optional[str] = None) -> bool:
        """
        Validate product IDs
        """
        if not isinstance(product_ids, list):
            return False
        
        for product_id in product_ids:
            # Check for injection in product IDs
            if isinstance(product_id, str):
                if self.detect_injection(product_id, user_id):
                    return False
                # Validate UUID format or numeric ID
                if not (re.match(r'^[a-f0-9-]{36}$', product_id) or product_id.isdigit()):
                    self._log_security_event(
                        "invalid_product_id",
                        user_id,
                        str(product_id),
                        "Invalid product ID format",
                        "MEDIUM"
                    )
                    return False
            elif isinstance(product_id, int):
                if product_id <= 0:
                    return False
        
        return True

    def _validate_message_structure(self, message: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """
        Validate message structure
        """
        required_fields = ["role", "content"]
        
        for field in required_fields:
            if field not in message:
                return False
        
        # Validate role
        if message["role"] not in ["system", "user", "assistant"]:
            return False
        
        # Validate content
        if not isinstance(message["content"], str):
            return False
        
        return True

    def _get_json_depth(self, json_str: str) -> int:
        """
        Calculate JSON nesting depth
        """
        depth = 0
        max_depth = 0
        
        for char in json_str:
            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth -= 1
        
        return max_depth

    def _log_security_event(self, event_type: str, user_id: Optional[str], input_text: str, details: str, severity: str):
        """
        Log security events
        """
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            input_text=input_text,
            pattern_matched=details,
            timestamp=datetime.now(),
            severity=severity
        )
        
        self.logger.warning(
            f"[SECURITY] ⚠️ {event_type} | User: {user_id} | Severity: {severity} | Details: {details}"
        )

class SecurityException(Exception):
    """Security-related exceptions"""
    pass
