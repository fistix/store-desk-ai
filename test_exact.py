#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"

def test_exact_match():
    """Test to exactly match what FastAPI receives"""
    print("🎯 EXACT MATCH TEST")
    print("=" * 40)
    
    # Test request - same as before
    test_request = {
        "sessionId": "test-session-123",
        "message": "Enable stock monitoring for selected products with threshold 5",
        "inputType": "text",
        "context": {
            "selectedProductIds": ["prod-1", "prod-2"],
            "connectorId": "test-connector"
        }
    }
    
    # Try different JSON serialization formats
    json_formats = [
        json.dumps(test_request),  # Default
        json.dumps(test_request, separators=(',', ':')),  # Compact
        json.dumps(test_request, separators=(',', ':'),  # With spaces
        json.dumps(test_request, separators=(',', ': ')),  # With space after colon
    ]
    
    for i, payload in enumerate(json_formats):
        print(f"\n🧪 Format {i+1}: {payload[:100]}...")
        
        timestamp = str(int(time.time()))
        message = timestamp.encode() + payload.encode()
        signature = hmac.new(
            HMAC_SECRET.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        
        print(f"⏰ Timestamp: {timestamp}")
        print(f"🔐 Signature: {signature}")
        
        headers = {
            "Content-Type": "application/json",
            "X-HMAC-Signature": signature,
            "X-Timestamp": timestamp,
            "X-User-Id": "test-user",
            "X-Tenant-Id": "test-tenant",
            "X-Connector-Id": "test-connector"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/storedesk/assist",
                headers=headers,
                json=test_request,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ SUCCESS with format {i+1}!")
                break
            else:
                print(f"❌ Format {i+1} failed: {response.status_code}")
                
        except Exception as e:
            print(f"💥 Format {i+1} error: {str(e)}")
    
    print("=" * 40)
    print("🎯 EXACT MATCH TEST COMPLETE")

if __name__ == "__main__":
    test_exact_match()
