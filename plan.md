# StoreDesk AI — Final Complete Implementation Plan

## Overview

A single Python AI microservice called **storedesk-ai** that accepts natural language and voice commands from agency operators managing dropshipping client stores. It reasons using a LangGraph agent, executes GraphQL mutations, and returns natural language responses. NodeJS acts as a secure proxy. A mock GraphQL server enables isolated development and testing. A NextJS test page validates the complete end to end flow.

---

## Part 1 — NodeJS Changes

### 1.1 Service Account API Key Infrastructure

Add a new API key validation middleware separate from existing JWT middleware. NodeJS maintains valid service account keys in environment variables stored as hashed values — never plaintext. Middleware checks for `X-Service-Key` header on protected internal routes. Completely independent of existing JWT auth — both coexist on different routes without interference.

### 1.2 New AI Gateway Endpoint

Add one new REST endpoint — `POST /api/storedesk/assist`. This endpoint:
- Validates incoming JWT from frontend using existing JWT middleware — no changes to existing auth logic
- Extracts user context from validated token — userId, tenantId, connectorId, email, permissions
- Validates and sanitizes request body
- Generates HMAC-SHA256 signature using shared secret + timestamp + raw request body
- Attaches signature, timestamp, and user context as headers to outgoing request
- Forwards enriched payload to storedesk-ai service
- Returns storedesk-ai response directly back to frontend
- Implements per-user rate limiting — 30 AI requests per minute per user
- Logs every AI request with userId, timestamp, inputType (text/audio) — never logs message content

### 1.3 Service Key Scoped Authorization

When storedesk-ai calls back into NodeJS GraphQL with `X-Service-Key`, NodeJS must:
- Verify service key against hashed value in env
- Validate presence of forwarded user context headers — `X-User-Id`, `X-Tenant-Id`, `X-Connector-Id`
- Allow access only to mutations listed in `STOREDESK_AI_ALLOWED_MUTATIONS` config
- Reject any mutation not on whitelist even with a valid service key
- Execute whitelisted mutation in context of the original user — existing permissions still apply

Initial whitelist:
```
updateBulkStockMonitoringCommand
updateBulkPriceMonitoringCommand
```

### 1.4 Environment Variables to Add

```
STOREDESK_AI_URL=http://storedesk-ai:8000
STOREDESK_AI_HMAC_SECRET=<strong-random-secret>
STOREDESK_AI_SERVICE_KEY=<hashed-service-key>
STOREDESK_AI_ALLOWED_MUTATIONS=updateBulkStockMonitoringCommand,updateBulkPriceMonitoringCommand
STOREDESK_AI_RATE_LIMIT_PER_USER=30
STOREDESK_AI_RATE_LIMIT_WINDOW_SECONDS=60
```

### 1.5 NodeJS Dependencies to Add

- `axios` or native `fetch` — calling storedesk-ai service
- `express-rate-limit` — per-user rate limiting on AI gateway endpoint
- `crypto` — built-in Node, HMAC signing, no new package needed

### 1.6 New or Modified Files

```
middleware/storedeskServiceKeyAuth.js   — new
middleware/storedeskRateLimit.js        — new
routes/storedesk.js                     — new
app.js                                  — modified, register new route
.env                                    — modified, add storedesk vars
```

---

## Part 2 — storedesk-mock-server

### 2.1 Purpose

A lightweight standalone NodeJS application that mimics the real NodeJS GraphQL API. storedesk-ai calls this mock server exactly as it would call the real backend — same mutations, same request format, same response shape, same auth headers. Enables storedesk-ai development and testing in complete isolation without risk of touching real data.

### 2.2 Technology Stack

- **Framework**: Express with Apollo Server
- **Port**: 4010 — matches real NodeJS server port so storedesk-ai needs zero config changes when switching between mock and real

### 2.3 Project Structure

```
storedesk-mock-server/
│
├── index.js                        # Express + Apollo Server entry point
├── package.json
├── .env.example
│
├── schema/
│   ├── typeDefs.js                 # GraphQL type definitions — mirrors real schema exactly
│   └── resolvers.js                # Mock resolvers with configurable scenario responses
│
├── middleware/
│   └── serviceKeyAuth.js           # X-Service-Key + user context header validation
│
├── config/
│   └── mockResponses.js            # Response definitions per scenario
│
└── README.md                       # How to run, how to configure scenarios
```

### 2.4 GraphQL Mutations Implemented

```
updateBulkStockMonitoringCommand(input: UpdateBulkStockMonitoringInput!)
  → { isSuccess, message }

updateBulkPriceMonitoringCommand(input: UpdateBulkPriceMonitoringInput!)
  → { isSuccess, message }
```

Input types mirror real schema exactly. As new mutations are added to the real server in future, they must be added here too — keeping mock and real in sync is part of the development contract.

### 2.5 Configurable Scenarios

Active scenario controlled by `MOCK_SCENARIO` env variable:

```
happy_path       — all mutations return isSuccess: true (default)
partial_failure  — stock monitoring succeeds, price monitoring fails
full_failure     — all mutations return isSuccess: false
slow_response    — artificial delay before responding, tests timeout and retry logic
server_error     — returns HTTP 500, tests storedesk-ai exponential backoff
auth_failure     — returns 401 regardless of service key
```

### 2.6 Auth Validation

Implements identical validation to real NodeJS server:
- Validates `X-Service-Key` header — rejects with 401 if missing or invalid
- Validates presence of `X-User-Id`, `X-Tenant-Id`, `X-Connector-Id` headers — rejects if any missing
- Service key shown in logs as `[PRESENT]` or `[MISSING]` — never logged in full

### 2.7 Request Logging

Every incoming GraphQL request logged to console:

```
[2026-04-04 10:23:41] Mutation: updateBulkStockMonitoringCommand
  Service Key:    [PRESENT]
  X-User-Id:      user-123
  X-Tenant-Id:    tenant-456
  X-Connector-Id: 557429f0-f887-4615-9cef-f57312ca5972
  Variables: {
    productIds: ["7626ff3a-...", "78561ba7-..."],
    bulkStockMonitoring: {
      isApplyToAllProducts: false,
      isQuantityEnabled: true,
      quantityThreshold: 5
    }
  }
  Active Scenario: happy_path
  Response: { isSuccess: true, message: "Stock monitoring updated successfully" }
```

### 2.8 Runtime Control Endpoints

```
POST   /mock/scenario          — change active scenario without restart
GET    /mock/scenario          — returns currently active scenario
GET    /mock/requests          — returns log of all requests since server start
DELETE /mock/requests          — clears request log
GET    /health                 — returns server status
```

### 2.9 Environment Variables

```
PORT=4010
MOCK_SERVICE_KEY=<must match STOREDESK_AI_SERVICE_KEY>
MOCK_SCENARIO=happy_path
MOCK_SLOW_RESPONSE_MS=3000
```

---

## Part 3 — storedesk-ai Python Microservice

### 3.1 Technology Stack

- **Framework**: FastAPI with async support
- **Agent Framework**: LangGraph for stateful agent loop
- **Session Store**: Redis for conversation memory and provider usage tracking
- **STT**: faster-whisper running fully local — no external API, no cost
- **HTTP Client**: httpx async for calling NodeJS GraphQL
- **Config**: Pydantic Settings with YAML provider config
- **Testing**: pytest with pytest-asyncio

### 3.2 Project Structure

```
storedesk-ai/
│
├── main.py                          # FastAPI app entry point
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── config/
│   ├── settings.py                  # Pydantic settings, all config from env
│   └── providers.yaml               # LLM provider priority, limits, models
│
├── core/
│   ├── auth.py                      # HMAC signature verification
│   ├── context.py                   # UserContext model
│   ├── gateway.py                   # FastAPI router, single entry point
│   ├── session_manager.py           # Redis conversation history and pending confirmation
│   ├── stt.py                       # faster-whisper STT, audio to text
│   └── graphql_client.py            # Async httpx, calls NodeJS mutations
│
├── providers/
│   ├── base.py                      # Abstract LLMProvider interface
│   ├── manager.py                   # Provider selection, usage tracking, fallback
│   ├── gemini.py                    # Google Gemini implementation
│   ├── groq.py                      # Groq implementation
│   ├── openai.py                    # OpenAI implementation
│   └── ollama.py                    # Ollama local implementation
│
├── agent/
│   ├── orchestrator.py              # Master LangGraph agent, domain routing
│   ├── base_agent.py                # Base class, shared reasoning logic
│   ├── base_tool.py                 # Base class for all tools
│   └── domains/
│       ├── __init__.py              # Master domain registry
│       └── products/
│           ├── __init__.py          # Product domain tool registry
│           ├── agent.py             # Product domain LangGraph agent
│           └── tools/
│               ├── stock_monitoring.py
│               └── price_monitoring.py
│
└── tests/
    ├── conftest.py                  # Fixtures, mock GraphQL client
    ├── test_auth.py
    ├── test_provider_manager.py
    ├── test_session_manager.py
    ├── test_orchestrator.py
    └── domains/
        └── products/
            ├── test_products_agent.py
            ├── test_stock_monitoring_tool.py
            └── test_price_monitoring_tool.py
```

### 3.3 API Endpoints

**Primary endpoint**: `POST /api/storedesk/assist`

Request body:
```
{
  "sessionId":        "string",
  "message":          "string | null",       // text input
  "audioBase64":      "string | null",       // audio input, mutually exclusive
  "inputType":        "text | audio",
  "context": {
    "selectedProductIds": ["uuid"],
    "connectorId":    "string"
  }
}
```

Headers attached by NodeJS:
```
X-HMAC-Signature:   <signature>
X-Timestamp:        <unix-timestamp>
X-User-Id:          <userId>
X-Tenant-Id:        <tenantId>
X-Connector-Id:     <connectorId>
```

Response body:
```
{
  "success":               true,
  "message":               "Natural language response to user",
  "actionsExecuted": [
    {
      "intent":            "UPDATE_STOCK_MONITORING",
      "success":           true,
      "affectedCount":     2
    }
  ],
  "requiresConfirmation":  false,
  "confirmationQuestion":  null,
  "clarificationQuestion": null,
  "activeProvider":        "gemini"
}
```

**Health endpoint**: `GET /health`
- Returns service status, Redis connectivity, configured providers availability
- Never exposes API keys or secrets

**Debug endpoints** — disabled in production via `DEBUG_ENDPOINTS_ENABLED=false`:

`GET /debug/session/{sessionId}` — full conversation history from Redis

`GET /debug/providers` — current usage counters and status per provider

### 3.4 Core — Auth Module

On every incoming request from NodeJS:
- Extract `X-HMAC-Signature` and `X-Timestamp` headers
- Reject immediately if timestamp is older than 30 seconds — replay attack prevention
- Recompute HMAC-SHA256 using shared secret + timestamp + raw request body
- Reject if computed signature does not match header value
- Return 401 on any failure — no detail in response body, never leak reason

### 3.5 Core — STT Module

Uses **faster-whisper** running fully local — no external API calls, no cost:
- Accept raw audio bytes — WebM, OGG, MP4, whatever browser MediaRecorder produces
- Convert to WAV mono 16kHz using ffmpeg internally before passing to faster-whisper — frontend sends whatever browser produces, normalization is internal
- Load model once on service startup, keep in memory — never reload per request
- Model size configurable via `WHISPER_MODEL_SIZE` env variable
- Return transcribed text string to gateway
- Log transcription confidence score for monitoring

Recommended model size per environment:
```
development:   tiny    — fastest startup, good enough for testing
staging:       base    — good balance of speed and accuracy
production:    small   — recommended for short command-style utterances
               medium  — if users have varied accents or non-native English
```

### 3.6 Core — Provider Manager

On startup load all providers from `providers.yaml`. On each LLM call:
- Iterate providers by priority order
- Check Redis usage counter for current provider against configured daily limit
- Check Redis status key — skip if `exhausted` or `backoff`
- Select first available provider
- After successful call increment usage counter in Redis
- On provider error — set status to `backoff` with 5 minute TTL, immediately try next provider
- Expose single method `complete(messages, tools, context)` — all callers are fully provider-agnostic

Tool calling capability per provider:
```
gemini:    native tool calling
groq:      native tool calling
openai:    native tool calling
ollama:    prompt-based structured JSON — parsed internally by ollama.py,
           converted to consistent tool call format before returning to agent
```

Provider priority order:
```
1. Google Gemini   gemini-2.0-flash         free tier   1500 req/day
2. Groq            llama-3.3-70b-versatile  free tier   14400 req/day
3. OpenAI          gpt-4o-mini              paid        no hard limit
4. Ollama          llama3.2                 local       always available
```

### 3.7 Core — Session Manager

Redis key patterns:
```
session:{sessionId}:history               — conversation turn list
session:{sessionId}:pending_confirmation  — awaiting user confirm or cancel
```

Conversation history rules:
- Store as ordered list of message objects — role and content per turn
- TTL of 2 hours per session, reset on every interaction
- Hard cap at last 20 turns — oldest turns dropped to prevent context window overflow
- New turn appended after every request/response cycle

Pending confirmation rules:
- Created when agent detects `isApplyToAllProducts: true`
- Contains pendingIntent, pendingParameters, connectorId, triggeredAt
- TTL of 5 minutes — auto-expires if user abandons
- Deleted immediately on confirm or cancel

### 3.8 Core — GraphQL Client

Async httpx client with connection pooling:
- Attach `X-Service-Key` header on every outgoing mutation request
- Attach forwarded user context headers — `X-User-Id`, `X-Tenant-Id`, `X-Connector-Id`
- Retry logic — 3 attempts with exponential backoff on 5xx errors only
- No retry on 4xx — auth failure or validation error will not resolve with retry
- Normalize all GraphQL errors into consistent error model returned to agent tools
- Request timeout of 10 seconds per attempt

### 3.9 Agent — Orchestrator

Master LangGraph stateful agent. Receives every request after HMAC auth and STT transcription. System prompt describes all available domains in the context of a dropshipping agency platform — managing client store listings, stock, pricing.

LangGraph state object:
```
{
  userMessage:           string,
  userContext:           UserContext,
  conversationHistory:   list,
  pendingConfirmation:   object | null,
  toolCallsMade:         list,
  toolResults:           list,
  iterationCount:        int,
  finalResponse:         object | null
}
```

**Confirmation resolution — checked before any reasoning begins:**

If `pendingConfirmation` exists in state:
- Message is affirmative (yes, confirm, proceed, ok, sure, do it) → route directly to domain agent with stored parameters, skip intent extraction entirely
- Message is negative (no, cancel, stop, nevermind, don't) → delete pending from Redis, return cancellation message, skip agent loop entirely
- Message is neither → return reminder: *"You have a pending action awaiting confirmation. Please confirm or cancel before sending a new command"* — do not process new command

**Normal reasoning loop when no pending confirmation:**
1. Analyze message against full conversation history for context
2. Identify which domain(s) are involved
3. If ambiguous or parameters missing — use `ask_clarification` tool
4. If single domain — invoke that domain agent
5. If multiple domains — invoke domain agents sequentially
6. Collect all results, compose unified natural language response

Max iterations guard — if `iterationCount` reaches 5 without resolution, return fallback: *"I wasn't able to complete that action. Could you rephrase your request?"*

### 3.10 Agent — Base Agent and Base Tool

**Base agent responsibilities:**
- Receive enriched user context and conversation history
- Build LangGraph graph with tools from domain tool registry
- Delegate all LLM calls through provider manager — never call provider directly
- Return structured result to orchestrator

**Base tool responsibilities:**
- Receive validated parameters and user context
- Call graphql_client with correct mutation name and parameters
- Return normalized `{ success, message, data, error }` to agent
- All domain tools inherit from base tool — only implement parameter building and mutation name

### 3.11 Agent — Products Domain

**Product Agent** system prompt describes product management in dropshipping agency context — managing stock alerts and price margin monitoring across client store listings.

**Stock Monitoring Tool:**
- Mutation: `updateBulkStockMonitoringCommand`
- Required parameters: `isQuantityEnabled` (bool), `quantityThreshold` (int, min 1), `isApplyToAllProducts` (bool)
- Conditional: `productIds` required if `isApplyToAllProducts` is false — validated against selectedProductIds in user context
- If `isApplyToAllProducts` is true — call `request_confirmation` tool instead of executing, halt loop

**Price Monitoring Tool:**
- Mutation: `updateBulkPriceMonitoringCommand`
- Required parameters: `isPriceEnabled` (bool), `priceThresholdPercentage` (float, min 0.1 max 100), `isApplyToAllProducts` (bool)
- Conditional: `productIds` required if `isApplyToAllProducts` is false
- If `isApplyToAllProducts` is true — call `request_confirmation` tool instead of executing, halt loop

### 3.12 Confirmation Flow — Complete

**Turn 1 — Detection and halt:**
- Domain agent extracts intent and parameters successfully
- Detects `isApplyToAllProducts: true`
- Calls `request_confirmation` tool with pendingIntent, pendingParameters, confirmationMessage
- `request_confirmation` saves to Redis with 5 minute TTL
- LangGraph loop ends cleanly
- Response returned: `requiresConfirmation: true`, `confirmationQuestion` populated, `actionsExecuted: []`

**Turn 2 — Resolution:**
- Gateway reads `session:{sessionId}:pending_confirmation` from Redis before passing to orchestrator
- Attaches pending context to LangGraph state
- Orchestrator resolves based on message content as described in section 3.9
- On confirm — execute stored intent, delete Redis key, return success response
- On cancel — delete Redis key, return cancellation message
- On expiry — pending key not found in Redis, treat as fresh request, if message is just "confirm" or "yes" return: *"Your previous action has expired. Please send your command again"*

### 3.13 Environment Variables

```
# Server
PORT=8000
ENVIRONMENT=development | production
DEBUG_ENDPOINTS_ENABLED=true | false

# Security
HMAC_SECRET=<must match NodeJS STOREDESK_AI_HMAC_SECRET>
NODEJS_GRAPHQL_URL=http://storedesk-mock-server:4010/graphql
SERVICE_ACCOUNT_KEY=<must match MOCK_SERVICE_KEY or real NodeJS key>

# Redis
REDIS_URL=redis://localhost:6379

# LLM Providers — all optional, service uses what is configured
GEMINI_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# STT
WHISPER_MODEL_SIZE=base

# Limits
SESSION_TTL_SECONDS=7200
MAX_HISTORY_TURNS=20
PROVIDER_BACKOFF_SECONDS=300
REQUEST_MAX_ITERATIONS=5
```

### 3.14 providers.yaml

```
providers:
  - name: gemini
    model: gemini-2.0-flash
    priority: 1
    api_key_env: GEMINI_API_KEY
    supports_tool_calling: true
    limit_type: requests_per_day
    limit: 1500
    reset: midnight_utc

  - name: groq
    model: llama-3.3-70b-versatile
    priority: 2
    api_key_env: GROQ_API_KEY
    supports_tool_calling: true
    limit_type: requests_per_day
    limit: 14400
    reset: midnight_utc

  - name: openai
    model: gpt-4o-mini
    priority: 3
    api_key_env: OPENAI_API_KEY
    supports_tool_calling: true
    limit_type: none

  - name: ollama
    model: llama3.2
    priority: 4
    api_key_env: null
    base_url_env: OLLAMA_BASE_URL
    supports_tool_calling: partial
    limit_type: none
```

---

## Part 4 — NextJS Test Page

### 4.1 Purpose and Access Guard

Standalone test page at `/storedesk-test`. Only rendered when `NEXT_PUBLIC_STOREDESK_TEST_ENABLED=true` — never visible in production. Allows developers and QA to validate the complete flow end to end without touching the real product UI.

### 4.2 Page Layout

Three panels side by side on desktop, stacked on mobile.

**Left Panel — Input Controls:**
- Textarea for typing commands
- Voice record button — starts and stops browser microphone via MediaRecorder API, sends audio blob as base64 to NodeJS on stop
- Selected Products section — 4 to 5 hardcoded product UUIDs as checkboxes, tester selects which to include in context
- ConnectorId input — prefilled from `NEXT_PUBLIC_TEST_CONNECTOR_ID` env variable
- Session ID display — auto-generated UUID on page load
- Reset Session button — clears Redis history via debug endpoint, generates new session ID
- Submit button — disabled during pending request

**Middle Panel — Conversation:**
- Chat-style message history
- User messages with user icon
- AI responses with storedesk-ai icon
- Active provider badge per response — gemini, groq, openai, or ollama
- If `requiresConfirmation: true` — Confirm and Cancel buttons inline below AI message, text input disabled until resolved
- If `clarificationQuestion` present — highlighted as distinct question bubble
- Actions Executed per response — intent name, success status, affected count
- Loading indicator during request

**Right Panel — Debug:**
- Raw request payload sent to NodeJS — prettified JSON
- Raw response from storedesk-ai — prettified JSON
- Mock Scenario selector — dropdown to call `POST /mock/scenario` and change active scenario at runtime
- Session Memory button — calls `GET /debug/session/{sessionId}`
- Provider Stats button — calls `GET /debug/providers`
- Mock Request Log button — calls `GET /mock/requests` to see what storedesk-mock-server received
- Clear Debug button

### 4.3 Pre-written Test Prompts

Collapsible section, click any prompt to auto-fill textarea:

```
Stock Monitoring:
  "Enable quantity monitoring for selected products with threshold 5"
  "Disable stock monitoring for all products"
  "Set stock alert to 10 units for selected products"
  "Turn off quantity monitoring for selected products"

Price Monitoring:
  "Enable price margin monitoring at 8 percent for selected products"
  "Disable price monitoring for all products"
  "Set price threshold to 5 percent for selected products"

Combined:
  "Enable both stock and price monitoring for selected products"
  "Disable all monitoring for selected products"
  "Set stock threshold to 3 and price margin to 10 percent for selected products"

Confirmation Flow:
  "Disable price monitoring for all products"  — triggers confirmation
  "Yes proceed"                                — confirms pending action
  "Cancel"                                     — cancels pending action

Edge Cases:
  "Enable monitoring"              — ambiguous, should trigger clarification
  "Set threshold to 5"             — ambiguous type, should trigger clarification
  "Yes"                            — no pending confirmation, should handle gracefully
```

---

## Part 5 — Adding Future Features

When any new AI feature needs to be added — orders management, messages, supplier operations, inventory:

```
1. Create domain folder:   agent/domains/orders/
2. Create agent:           agent/domains/orders/agent.py        inherits base_agent
3. Create tools folder:    agent/domains/orders/tools/
4. Create tool per mutation: agent/domains/orders/tools/update_order_status.py  inherits base_tool
5. Register domain:        agent/domains/__init__.py            add orders entry
6. Whitelist mutations:    NodeJS .env                          append to STOREDESK_AI_ALLOWED_MUTATIONS
7. Add mock mutations:     storedesk-mock-server/schema/        add to typeDefs and resolvers
```

Nothing else changes. NodeJS gateway, HMAC auth, session manager, provider manager, orchestrator, Redis structure, Docker setup — all unchanged.

---

## Part 6 — Deployment

### Docker Compose — Development

```
services:

  nodejs:
    existing service
    add STOREDESK_AI_* env vars
    network: storedesk-network

  storedesk-ai:
    build: ./storedesk-ai
    no published ports — internal only
    depends_on: redis
    env: NODEJS_GRAPHQL_URL=http://storedesk-mock-server:4010/graphql
    network: storedesk-network

  storedesk-mock-server:
    build: ./storedesk-mock-server
    no published ports — internal only
    network: storedesk-network

  redis:
    image: redis:7-alpine
    no published ports — internal only
    network: storedesk-network

  ollama:
    image: ollama/ollama
    optional — comment out if not needed
    network: storedesk-network

networks:
  storedesk-network:
    driver: bridge
```

### Docker Compose Override — Integration Testing

`docker-compose.integration.yml` overrides storedesk-ai to point at real NodeJS instead of mock:

```
services:
  storedesk-ai:
    environment:
      NODEJS_GRAPHQL_URL: http://nodejs:4010/graphql
```

Run with: `docker-compose -f docker-compose.yml -f docker-compose.integration.yml up`

### Secrets Management

- Never commit API keys, HMAC secret, or service account key
- Use `.env` files locally — `.env` in `.gitignore`
- `HMAC_SECRET` must be identical in NodeJS and storedesk-ai env
- `SERVICE_ACCOUNT_KEY` in storedesk-ai must match `MOCK_SERVICE_KEY` in mock server (dev) and `STOREDESK_AI_SERVICE_KEY` in real NodeJS (production)
- Document the key matching requirement clearly in project README
- Production — AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault

### Health Check Integration

NodeJS checks `GET http://storedesk-ai:8000/health` before forwarding AI requests. If storedesk-ai is unhealthy, NodeJS returns user-friendly error to frontend — *"AI assistant is temporarily unavailable, please try again shortly"* — rather than a timeout or cryptic error.

---

## Complete File Summary

**NodeJS real server — new or modified:**
```
middleware/storedeskServiceKeyAuth.js
middleware/storedeskRateLimit.js
routes/storedesk.js
app.js                                  modified — register new route
.env                                    modified — add storedesk vars
```

**storedesk-mock-server — all new:**
```
index.js
package.json
.env.example
schema/typeDefs.js
schema/resolvers.js
middleware/serviceKeyAuth.js
config/mockResponses.js
README.md
```

**storedesk-ai — all new:**
```
main.py
requirements.txt
Dockerfile
.env.example
config/settings.py
config/providers.yaml
core/auth.py
core/context.py
core/gateway.py
core/session_manager.py
core/stt.py
core/graphql_client.py
providers/base.py
providers/manager.py
providers/gemini.py
providers/groq.py
providers/openai.py
providers/ollama.py
agent/orchestrator.py
agent/base_agent.py
agent/base_tool.py
agent/domains/__init__.py
agent/domains/products/__init__.py
agent/domains/products/agent.py
agent/domains/products/tools/stock_monitoring.py
agent/domains/products/tools/price_monitoring.py
tests/conftest.py
tests/test_auth.py
tests/test_provider_manager.py
tests/test_session_manager.py
tests/test_orchestrator.py
tests/domains/products/test_products_agent.py
tests/domains/products/test_stock_monitoring_tool.py
tests/domains/products/test_price_monitoring_tool.py
```

**NextJS — new:**
```
pages/storedesk-test.jsx
or
app/storedesk-test/page.jsx
```

**Docker — new or modified:**
```
docker-compose.yml                      modified — add new services
docker-compose.integration.yml          new — integration test override
```

---

## Key Principles

```
NodeJS                — secure proxy only, zero AI logic, existing code untouched
storedesk-mock-server — isolated GraphQL mock, configurable scenarios, full request logging
storedesk-ai          — single Python service, owns full AI reasoning loop end to end
Orchestrator          — routes by domain, handles confirmation and clarification
Domain Agents         — own reasoning per business area, independently testable
Tools                 — one per mutation, thin execution layer, inherit base_tool
Providers             — YAML configurable, auto-fallback, free tiers first, local last
STT                   — faster-whisper, fully local, zero cost, zero external API
Security              — HMAC between NodeJS and storedesk-ai, scoped service key for mutations
Future features       — new domain folder + tools only, nothing else ever changes
```