#!/usr/bin/env python3
import requests
import hmac
import hashlib
import time
import json

BASE_URL = "http://localhost:8000"
HMAC_SECRET = "test-hmac-secret"

def test_final():
    print("🎯 FINAL TEST")
    print("=" * 40)
    
    # Exact same request structure
    test_request = {
        "sessionId": "test-session-123",
        "message": "Enable stock monitoring for selected products with threshold 5",
        "inputType": "text",
        "context": {
            "selectedProductIds": ["prod-1", "prod-2"],
            "connectorId": "test-connector"
        }
    }
    
    # Use compact JSON to match what FastAPI receives
    payload = json.dumps(test_request, separators=(',', ':'))
    timestamp = str(int(time.time()))
    
    # Exact same computation as auth.py
    message = timestamp.encode() + payload.encode()
    signature = hmac.new(HMAC_SECRET.encode(), message, hashlib.sha256).hexdigest()
    
    print(f"📝 Payload: {repr(payload)}")
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
        response = requests.post(BASE_URL + "/api/storedesk/assist", headers=headers, data=payload, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! FLOW WORKING!")
            print(f"💬 AI Response: {result.get('message', 'No message')}")
            print(f"🔧 Actions: {result.get('actionsExecuted', [])}")
            print(f"🤖 Provider: {result.get('activeProvider', 'Unknown')}")
            
            # Show the complete flow trace
            if 'toolCallsMade' in result:
                print(f"🔧 Tool Calls: {len(result['toolCallsMade'])}")
            if 'requiresConfirmation' in result:
                print(f"❓ Confirmation Required: {result['requiresConfirmation']}")
                
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"💥 Error: {str(e)}")
    
    print("=" * 40)
    print("🎯 FINAL TEST COMPLETE")

if __name__ == "__main__":
    test_final()
