#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"

def test_hmac_debug():
    """Debug HMAC signature generation"""
    print("🔍 HMAC SIGNATURE DEBUG")
    print("=" * 40)
    
    # Test request
    test_request = {
        "sessionId": "test-session-123",
        "message": "Enable stock monitoring for selected products with threshold 5",
        "inputType": "text",
        "context": {
            "selectedProductIds": ["prod-1", "prod-2"],
            "connectorId": "test-connector"
        }
    }
    
    payload = json.dumps(test_request, separators=(',', ':'))
    timestamp = str(int(time.time()))
    
    print(f"📝 Payload: {payload}")
    print(f"⏰ Timestamp: {timestamp}")
    print(f"🔢 Timestamp bytes: {timestamp.encode()}")
    print(f"📦 Payload bytes: {payload.encode()}")
    
    signature = generate_signature(timestamp, payload)
    
    print(f"🔐 Signature: {signature}")
    
    # Test with generated signature
    print(f"🔐 Method 2 (string concat): {signature2}")
    print(f"🔐 Method 3 (f-string): {signature3}")
    
    # Test with method 1 (matches auth.py)
    headers = {
        "Content-Type": "application/json",
        "X-HMAC-Signature": signature1,
        "X-Timestamp": timestamp,
        "X-User-Id": "test-user",
        "X-Tenant-Id": "test-tenant",
        "X-Connector-Id": "test-connector"
    }
    
    print(f"\n📡 Testing with Method 1...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/storedesk/assist",
            headers=headers,
            json=test_request,
            timeout=10
        )
        print(f"📊 Status: {response.status_code}")
        if response.status_code != 200:
            print(f"📝 Error: {response.text}")
    except Exception as e:
        print(f"💥 Error: {str(e)}")
    
    print("=" * 40)
    print("🎯 DEBUG COMPLETE")

if __name__ == "__main__":
    test_hmac_debug()
