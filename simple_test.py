#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"

def test_simple_flow():
    """Simple test to verify flow works"""
    print("🚀 SIMPLE FLOW TEST")
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
    
    # Generate exactly like service expects
    payload = json.dumps(test_request, separators=(',', ':'))
    timestamp = str(int(time.time()))
    
    # Match auth.py exactly: timestamp.encode() + body
    message = timestamp.encode() + payload.encode()
    signature = hmac.new(
        HMAC_SECRET.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    print(f"📝 Payload: {payload}")
    print(f"⏰ Timestamp: {timestamp}")
    print(f"🔐 Signature: {signature}")
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
        print("📡 Sending request...")
        response = requests.post(
            f"{BASE_URL}/api/storedesk/assist",
            headers=headers,
            json=test_request,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Complete flow working!")
            print(f"💬 AI Response: {result.get('message', 'No message')}")
            print(f"🔧 Actions: {result.get('actionsExecuted', [])}")
            print(f"🤖 Provider: {result.get('activeProvider', 'Unknown')}")
            
            # Check for confirmation requirement
            if result.get('requiresConfirmation'):
                print(f"❓ Confirmation Needed: {result.get('confirmationQuestion')}")
            else:
                print("✅ No confirmation needed")
                
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"📝 Detail: {response.text}")
            
    except Exception as e:
        print(f"💥 REQUEST FAILED: {str(e)}")
    
    print("=" * 40)
    print("🎯 TEST COMPLETE")

if __name__ == "__main__":
    test_simple_flow()
