#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"

def generate_signature(timestamp, payload):
    message = timestamp.encode() + payload.encode()
    signature = hmac.new(HMAC_SECRET.encode(), message, hashlib.sha256).hexdigest()
    return signature

def test_working_flow():
    print("🎯 WORKING FLOW TEST")
    print("=" * 40)
    
    test_request = {
        "sessionId": "test-session-123",
        "message": "Enable stock monitoring for selected products with threshold 5",
        "inputType": "text",
        "context": {
            "selectedProductIds": ["prod-1", "prod-2"],
            "connectorId": "test-connector"
        }
    }
    
    # Use default JSON serialization
    payload = json.dumps(test_request)
    timestamp = str(int(time.time()))
    signature = generate_signature(timestamp, payload)
    
    print(f"📝 Payload: {payload}")
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
        print("📡 Sending request...")
        response = requests.post(BASE_URL + "/api/storedesk/assist", headers=headers, json=test_request, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"💬 Message: {result.get('message', 'No message')}")
            print(f"🔧 Actions: {result.get('actionsExecuted', [])}")
            print(f"🤖 Provider: {result.get('activeProvider', 'Unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"💥 Error: {str(e)}")
    
    print("=" * 40)
    print("🎯 TEST COMPLETE")

if __name__ == "__main__":
    test_working_flow()
