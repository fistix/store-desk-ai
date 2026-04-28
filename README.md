# StoreDesk AI - Complete Implementation

A comprehensive AI-powered dropshipping store management system with natural language and voice command processing.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NextJS UI     │────│   NodeJS Proxy  │────│  StoreDesk AI   │
│   (Test Page)   │    │   (Backend)     │    │  (Python)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                │                       │
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Mock GraphQL    │    │   Redis         │
                       │ Server          │    │   (Sessions)    │
                       └─────────────────┘    └─────────────────┘
```

## Components

- **NodeJS Backend**: Secure proxy with HMAC authentication and rate limiting
- **StoreDesk AI**: Python microservice with LangGraph agent reasoning
- **Mock GraphQL Server**: Isolated testing environment with configurable scenarios
- **NextJS Test Page**: Complete UI for end-to-end testing
- **Redis**: Session management and provider usage tracking

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.9+ (for local development)

### Using Docker Compose (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <repository>
   cd store-desk-ai
   ```

2. **Configure environment:**
   ```bash
   # Copy example environment files
   cp backend/.env.example backend/.env
   cp storedesk-mock-server/.env.example storedesk-mock-server/.env
   cp storedesk-ai/.env.example storedesk-ai/.env
   cp frontend/.env.example frontend/.env
   
   # Edit backend/.env and add your secrets
   # At minimum, update:
   # - STOREDESK_AI_HMAC_SECRET (generate a strong random string)
   # - STOREDESK_AI_SERVICE_KEY (hash of your service key)
   ```

3. **Start all services:**
   ```bash
   # For development with hot reloading
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   
   # For production (no hot reloading)
   docker-compose up -d
   ```

4. **Access the test interface:**
   - Open http://localhost:3000/storedesk-test
   - The test page allows you to validate the complete flow

### Development with Hot Reloading

The development setup mounts source code volumes so changes reflect immediately:

- **NodeJS services**: Uses `nodemon` for automatic restart on file changes
- **Python service**: Uses `uvicorn --reload` for automatic restart
- **NextJS frontend**: Built-in hot reloading
- **Source code**: Mounted from host to container

**Benefits:**
- Edit code on your host machine
- Changes automatically reflected in containers
- No need to rebuild images for code changes
- Full debugging capabilities

## Production Deployment

### Production Docker Compose

For production deployment without source code mounting:

```bash
# Set up production environment
cp .env.production.example .env.production
# Edit .env.production with your actual secrets

# Deploy with production images
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Production Dockerfiles

Each service has an optimized production Dockerfile:

- `Dockerfile.prod` - Multi-stage builds
- Security hardening (non-root users)
- Health checks included
- Optimized image sizes
- Production dependencies only

### Environment Variables

Production requires these security variables:

```bash
# Required for HMAC authentication
STOREDESK_AI_HMAC_SECRET=your-secure-secret
STOREDESK_AI_SERVICE_KEY=hashed-service-key
HMAC_SECRET=must-match-backend
SERVICE_ACCOUNT_KEY=must-match-backend

# At least one LLM provider
GEMINI_API_KEY=your-key
# OR GROQ_API_KEY, OPENAI_API_KEY, etc.
```

### Deployment Options

#### 1. **Manual Production (Recommended)**
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

#### 2. **Cloud Services**
- **AWS ECS**: Use docker-compose.prod.yml as task definition
- **Google Cloud Run**: Deploy individual services
- **Azure Container Instances**: Import docker-compose.prod.yml

#### 3. **CI/CD Integration**
The project is ready for any CI/CD platform:
- Jenkins, GitLab CI, Azure DevOps, etc.
- Use the production Dockerfiles for consistent builds
- Environment variables for secure secret management

### Production Considerations

- ✅ **No source code mounting** - Images are self-contained
- ✅ **Health checks** - All services include health monitoring
- ✅ **Security** - Non-root users, minimal attack surface
- ✅ **Optimization** - Multi-stage builds, production dependencies only
- ✅ **Monitoring** - Ready for logging and metrics
- ✅ **Scalability** - Redis clustering, load balancer ready

## Local Development

### Backend (NodeJS)

```bash
cd backend
npm install
cp .env.example .env
# Edit .env with your configuration
npm start
```

### StoreDesk AI (Python)

```bash
cd storedesk-ai
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys and configuration
python main.py
```

### Mock GraphQL Server

```bash
cd storedesk-mock-server
npm install
cp .env.example .env
npm start
```

### NextJS Test Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Configuration

### LLM Providers

The AI service supports multiple providers with automatic fallback:

1. **Google Gemini** (free tier, 1500 requests/day)
2. **Groq** (free tier, 14400 requests/day)  
3. **OpenAI** (paid, no hard limit)
4. **Ollama** (local, always available)

Configure API keys in `storedesk-ai/.env`:

```bash
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
OLLAMA_BASE_URL=http://localhost:11434
```

### Security Configuration

**Critical**: The following secrets must match between services:

- `STOREDESK_AI_HMAC_SECRET` in backend/.env must equal `HMAC_SECRET` in storedesk-ai/.env
- `STOREDESK_AI_SERVICE_KEY` (hashed) in backend/.env must equal `MOCK_SERVICE_KEY` in storedesk-mock-server/.env

To generate a hashed service key:

```bash
# Generate service key
echo -n "your-service-key" | sha256sum

# Use the hash as STOREDESK_AI_SERVICE_KEY
# Use the plain key as MOCK_SERVICE_KEY
```

## Test Interface Features

The NextJS test page at `/storedesk-test` provides:

- **Text and voice input** for natural language commands
- **Product selection** with test data
- **Conversation history** with AI responses
- **Debug panel** showing raw requests/responses
- **Mock scenario selector** for testing different outcomes
- **Pre-written test prompts** for common operations

### Test Prompts

**Stock Monitoring:**
- "Enable quantity monitoring for selected products with threshold 5"
- "Disable stock monitoring for all products"

**Price Monitoring:**
- "Enable price margin monitoring at 8 percent for selected products"
- "Set price threshold to 5 percent for selected products"

**Confirmation Flow:**
- "Disable price monitoring for all products" (triggers confirmation)
- "Yes proceed" (confirms pending action)

## Mock Server Scenarios

The mock GraphQL server supports configurable scenarios:

- `happy_path`: All mutations succeed
- `partial_failure`: Stock succeeds, price fails
- `full_failure`: All mutations fail
- `slow_response`: Artificial delay for timeout testing
- `server_error`: Returns HTTP 500
- `auth_failure`: Always returns 401

Change scenarios via the test interface or API:

```bash
curl -X POST http://localhost:4010/mock/scenario -d '{"scenario":"full_failure"}'
```

## API Endpoints

### NodeJS Backend

- `POST /api/storedesk/assist` - AI gateway endpoint
- `POST /graphql` - GraphQL endpoint (service-to-service)
- `GET /health` - Health check

### Mock Server

- `POST /graphql` - GraphQL mutations
- `POST /mock/scenario` - Change test scenario
- `GET /mock/scenario` - Get current scenario
- `GET /mock/requests` - View request logs
- `DELETE /mock/requests` - Clear logs
- `GET /health` - Health check

### StoreDesk AI

- `POST /api/storedesk/assist` - Main AI endpoint
- `GET /health` - Service health check
- `GET /debug/session/{sessionId}` - Session history (dev only)
- `GET /debug/providers` - Provider status (dev only)

## Supported Operations

### Stock Monitoring
- Enable/disable quantity alerts
- Set threshold values
- Apply to specific products or all products

### Price Monitoring  
- Enable/disable price margin monitoring
- Set percentage thresholds
- Apply to specific products or all products

## Adding New Features

To add new AI capabilities (orders, messages, suppliers, etc.):

1. **Create domain folder:** `agent/domains/orders/`
2. **Create agent:** `agent/domains/orders/agent.py`
3. **Create tools:** `agent/domains/orders/tools/`
4. **Register domain:** Update `agent/domains/__init__.py`
5. **Whitelist mutations:** Add to `STOREDESK_AI_ALLOWED_MUTATIONS`
6. **Add mock mutations:** Update storedesk-mock-server schema

## Monitoring and Logging

- All AI requests are logged with userId and timestamp (never message content)
- Mock server logs detailed request information
- Provider usage tracked in Redis
- Health checks available on all services

## Production Deployment

### Security Considerations

- Use strong, unique secrets for HMAC and service keys
- Enable HTTPS in production
- Use proper secret management (AWS Secrets Manager, etc.)
- Disable debug endpoints in production
- Implement proper JWT authentication

### Scaling

- Redis can be clustered for high availability
- Multiple instances of storedesk-ai can be run behind a load balancer
- Consider CDN for frontend assets
- Monitor provider usage and rate limits

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check service key configuration
2. **HMAC Signature Mismatch**: Ensure secrets match between services
3. **Provider Exhausted**: Check Redis provider status and limits
4. **Connection Refused**: Verify Docker containers are running and networked

### Debug Mode

Enable debug endpoints in storedesk-ai:

```bash
DEBUG_ENDPOINTS_ENABLED=true
```

Access debug information at:
- `/debug/session/{sessionId}` - View conversation history
- `/debug/providers` - Check provider status and usage

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation for new features
4. Ensure all environment variables are documented

## License

[Add your license information here]
