# StoreDesk Mock GraphQL Server

A lightweight mock GraphQL server that mimics the real NodeJS GraphQL API for isolated development and testing of StoreDesk AI.

## Purpose

- Enables storedesk-ai development without touching real data
- Provides configurable scenarios for testing different outcomes
- Logs all requests for debugging
- Implements identical auth validation to production

## Quick Start

```bash
npm install
cp .env.example .env
npm start
```

The server will start on port 4010.

## Environment Variables

```bash
PORT=4010
MOCK_SERVICE_KEY=test-service-key
MOCK_SCENARIO=happy_path
MOCK_SLOW_RESPONSE_MS=3000
```

## Available Scenarios

- `happy_path` - All mutations return success (default)
- `partial_failure` - Stock succeeds, price fails
- `full_failure` - All mutations fail
- `slow_response` - Artificial delay before responding
- `server_error` - Returns HTTP 500
- `auth_failure` - Always returns 401

## API Endpoints

### GraphQL
- `POST /graphql` - GraphQL mutations (requires auth)

### Control Endpoints
- `POST /mock/scenario` - Change active scenario
- `GET /mock/scenario` - Get current scenario
- `GET /mock/requests` - View request logs
- `DELETE /mock/requests` - Clear logs
- `GET /health` - Health check

## Supported Mutations

```graphql
updateBulkStockMonitoringCommand(input: UpdateBulkStockMonitoringInput!): UpdateResponse!
updateBulkPriceMonitoringCommand(input: UpdateBulkPriceMonitoringInput!): UpdateResponse!
```

## Authentication

The server validates:
- `X-Service-Key` header (must match `MOCK_SERVICE_KEY`)
- `X-User-Id`, `X-Tenant-Id`, `X-Connector-Id` headers

## Usage in Testing

Use the control endpoints to simulate different conditions:

```bash
# Test failure scenario
curl -X POST http://localhost:4010/mock/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario":"full_failure"}'

# Test slow response
curl -X POST http://localhost:4010/mock/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario":"slow_response"}'

# View request logs
curl http://localhost:4010/mock/requests
```
