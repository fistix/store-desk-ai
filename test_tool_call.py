#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_tool_call():
    print("🔧 TESTING TOOL CALL TRIGGER")
    print("=" * 50)
    
    # Request that should definitely trigger tool calls
    test_request = {
        "sessionId": "test-session-123",
        "message": "Please enable stock monitoring for product ABC-123 with quantity threshold 10",
        "inputType": "text",
        "context": {
            "selectedProductIds": ["ABC-123"],
            "connectorId": "test-connector"
        }
    }
    
    print(f"📝 Request: {test_request['message']}")
    print(f"🆔 Product IDs: {test_request['context']['selectedProductIds']}")
    
    try:
        response = requests.post(
            BASE_URL + "/api/storedesk/assist",
            headers={
                "Content-Type": "application/json",
                "X-User-Id": "test-user",
                "X-Tenant-Id": "test-tenant", 
                "X-Connector-Id": "test-connector"
            },
            json=test_request,
            timeout=30
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"💬 Response: {result.get('message', 'No message')}")
            print(f"🔧 Actions: {result.get('actionsExecuted', [])}")
            print(f"🤖 Provider: {result.get('activeProvider', 'Unknown')}")
            print(f"📋 Tool Calls: {result.get('toolCallsMade', [])}")
            
            # Check if tools were called
            tool_calls = result.get('toolCallsMade', [])
            if tool_calls:
                print(f"🎯 TOOLS CALLED: {len(tool_calls)}")
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get('function', {}).get('name', 'unknown')
                    print(f"  🔧 Tool {i+1}: {tool_name}")
            else:
                print("⚠️ NO TOOLS CALLED - LLM gave text response only")
                
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"📝 Detail: {response.text}")
            
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
    
    print("=" * 50)
    print("🎯 TOOL CALL TEST COMPLETE")

if __name__ == "__main__":
    test_tool_call()
