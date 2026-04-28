#!/usr/bin/env python3
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"

def test_flow_no_hmac():
    """Test the AI flow without HMAC"""
    print("🚀 TESTING STOREDESK AI FLOW (NO HMAC)")
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
    
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": "test-user",
        "X-Tenant-Id": "test-tenant",
        "X-Connector-Id": "test-connector"
    }
    
    print(f"📝 Request: {test_request['message']}")
    print()
    
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
    test_flow_no_hmac()
