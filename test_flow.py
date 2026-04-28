#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"  # Must match storedesk-ai .env

def generate_signature(timestamp, payload):
    """Generate HMAC signature for testing"""
    message = timestamp.encode() + payload.encode()
    signature = hmac.new(
        HMAC_SECRET.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature

def test_ai_flow():
    """Test the complete AI flow with tracing"""
    print("🚀 TESTING STOREDESK AI FLOW")
    print("=" * 50)
    
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
    
    payload = json.dumps(test_request)
    timestamp = str(int(time.time()))
    signature = generate_signature(timestamp, payload)
    
    print(f"📝 Request: {test_request['message']}")
    print(f"🔐 Signature: {signature}")
    print(f"⏰ Timestamp: {timestamp}")
    print()
    
    headers = {
        "Content-Type": "application/json",
        "X-HMAC-Signature": signature,
        "X-Timestamp": timestamp,
        "X-User-Id": "test-user",
        "X-Tenant-Id": "test-tenant",
        "X-Connector-Id": "test-connector"
    }
    
    try:
        print("📡 Sending request to AI service...")
        response = requests.post(
            f"{BASE_URL}/api/storedesk/assist",
            headers=headers,
            json=test_request,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Response received:")
            print(f"💬 Message: {result.get('message', 'No message')}")
            print(f"🔧 Actions: {result.get('actionsExecuted', [])}")
            print(f"🤖 Provider: {result.get('activeProvider', 'Unknown')}")
            if result.get('requiresConfirmation'):
                print(f"❓ Confirmation Required: {result.get('confirmationQuestion')}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"📝 Error Detail: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"💥 REQUEST FAILED: {str(e)}")
    
    print("=" * 50)
    print("🎯 FLOW TEST COMPLETE")

if __name__ == "__main__":
    test_ai_flow()
