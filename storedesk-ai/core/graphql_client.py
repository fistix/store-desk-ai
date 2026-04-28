import httpx
import json
import time
from config.settings import settings
from fastapi import HTTPException
from httpx import AsyncClient, ConnectError, HTTPStatusError

class GraphQLClient:
    def __init__(self):
        self.client = AsyncClient(base_url=settings.NODEJS_GRAPHQL_URL, timeout=10)
        self.service_key = settings.SERVICE_ACCOUNT_KEY

    async def execute_mutation(self, mutation_name: str, variables: dict, user_context: dict) -> dict:
        query = f"""mutation {mutation_name}($input: {mutation_name}Input!) {{
            {mutation_name}(input: $input) {{
                isSuccess
                message
            }}
        }}"""
        payload = {"query": query, "variables": {"input": variables}}

        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key,
            "X-User-Id": user_context.get("user_id"),
            "X-Tenant-Id": user_context.get("tenant_id"),
            "X-Connector-Id": user_context.get("connector_id"),
        }

        attempts = 0
        max_attempts = 3
        backoff_factor = 0.5

        while attempts < max_attempts:
            try:
                response = await self.client.post(
                    "",
                    headers=headers,
                    content=json.dumps(payload),
                )
                response.raise_for_status()
                data = response.json()
                print(f"[GRAPHQL_CLIENT] 📦 Response data: {data}")
                
                # Normalize GraphQL errors into a consistent error model
                if data.get("errors"):
                    return {"success": False, "message": data["errors"][0]["message"], "data": None, "error": data["errors"]}
                
                # Check if data exists and has the mutation key
                if not data.get("data"):
                    return {"success": False, "message": "No data in response", "data": None, "error": "Missing data field"}
                
                # Try to get the mutation result, handle case where key might not exist
                if mutation_name in data["data"]:
                    return {"success": True, "message": "Mutation executed", "data": data["data"][mutation_name], "error": None}
                else:
                    # Return whatever data is available
                    print(f"[GRAPHQL_CLIENT] ⚠️ Mutation key '{mutation_name}' not found in response")
                    print(f"[GRAPHQL_CLIENT] 📋 Available keys: {list(data['data'].keys())}")
                    return {"success": True, "message": "Mutation executed (partial response)", "data": data["data"], "error": None}
            except HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    # 4xx errors should not be retried
                    raise HTTPException(status_code=e.response.status_code, detail=f"GraphQL client error: {e.response.text}")
                elif e.response.status_code >= 500:
                    # Retry for 5xx errors
                    print(f"Attempt {attempts + 1} failed with 5xx error: {e.response.status_code}. Retrying...")
                    await httpx.AsyncClient().aclose()
                    await httpx.AsyncClient(base_url=settings.NODEJS_GRAPHQL_URL, timeout=10).aclose()
                    time.sleep(backoff_factor * (2 ** attempts))
                    attempts += 1
            except ConnectError as e:
                print(f"Attempt {attempts + 1} failed with connection error: {e}. Retrying...")
                await httpx.AsyncClient().aclose()
                await httpx.AsyncClient(base_url=settings.NODEJS_GRAPHQL_URL, timeout=10).aclose()
                time.sleep(backoff_factor * (2 ** attempts))
                attempts += 1
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Unexpected error in GraphQL client: {e}")
        
        raise HTTPException(status_code=504, detail="GraphQL service unavailable after multiple retries")

graphql_client = GraphQLClient()
