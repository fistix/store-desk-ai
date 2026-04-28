#!/usr/bin/env python3
import hmac
import hashlib
import time
import json
import requests

# Configuration
HMAC_SECRET = "Kj9#mP2@nQ5!wR3&tY7*vB1^eF6%zA0"  # Updated from env
SERVICE_KEY = "688c37ca7d2c0c91b79096e28232343628c96e4e593c83473bc981334aaa7ff3"
AI_SERVICE_URL = "http://localhost:8000/api/storedesk/assist"

# Request data
request_data = {
    "sessionId": "test-session-123",
    "inputType": "text",
    "message": "What is the status of my products?"
}

# Generate timestamp
timestamp = str(int(time.time()))

# Convert request to JSON
body = json.dumps(request_data).encode()

# Generate HMAC signature
message = timestamp.encode() + body
signature = hmac.new(
    HMAC_SECRET.encode(),
    message,
    hashlib.sha256
).hexdigest()

# Headers
headers = {
    "Content-Type": "application/json",
    "X-User-Id": "test-user",
    "X-Tenant-Id": "test-tenant", 
    "X-Connector-Id": "test-connector",
    "X-Service-Key": SERVICE_KEY,
    "X-HMAC-Signature": signature,
    "X-Timestamp": timestamp
}

print("Sending test request to AI service...")
print(f"Timestamp: {timestamp}")
print(f"Signature: {signature}")
print(f"Request body: {json.dumps(request_data, indent=2)}")

# Make the request
try:
    response = requests.post(AI_SERVICE_URL, json=request_data, headers=headers)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
