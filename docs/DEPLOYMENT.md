# Deployment and development

This document contains the operational detail kept out of the portfolio-focused README.

## Local development with Docker Compose

Copy the example configuration and provide at least one supported LLM key:

```bash
cp .env.production.example .env.dev
# Set GEMINI_API_KEY or OPENAI_API_KEY in .env.dev
```

Start the development stack with source mounts and hot reload. Docker Compose
automatically merges `docker-compose.yml` and `docker-compose.override.yml`;
the override loads `.env.dev` into the relevant services.

```bash
docker compose up --build
```

The services are:

- Next.js demo UI: `http://localhost:3000/storedesk-test`
- Node.js gateway: `http://localhost:4010`
- FastAPI AI service: `http://localhost:8000`
- Mock GraphQL server: internal Compose service
- Redis: internal Compose service

Stop the stack with:

```bash
docker compose down
```

## Service-by-service development

### Node.js gateway

```bash
cd backend
cp .env.example .env
npm install
npm start
```

### AI service

```bash
cd storedesk-ai
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Mock GraphQL server

```bash
cd storedesk-mock-server
cp .env.example .env
npm install
npm start
```

### Next.js frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Production-style Compose

The production Compose file uses production Dockerfiles without source mounts:

```bash
cp .env.production.example .env.production
# Replace every placeholder and provide an LLM key.

docker compose --env-file .env.production \
  -f docker-compose.prod.yml up --build -d
```

Do not use the development HMAC or service keys in an internet-facing environment.

## Required configuration

### Shared HMAC secret

The values below must match:

- `STOREDESK_AI_HMAC_SECRET` in the Node.js gateway
- `HMAC_SECRET` in the FastAPI service

The gateway signs `timestamp + raw JSON body` using HMAC-SHA256. The AI service rejects missing, invalid, or stale signatures.

### GraphQL service key

The service account key used by the AI GraphQL client must match the backend or mock server configuration. Follow the expected plain-text/hash convention in the service-specific example files.

### LLM provider

Configure at least one provider loaded by `storedesk-ai/providers/manager.py`:

```dotenv
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
```

If both are configured, Gemini is attempted before OpenAI.

## Production checklist

- Store secrets in the cloud secret manager, not in Compose files or Git.
- Terminate TLS before the Node.js gateway.
- Derive user, tenant, connector, and permissions from verified identity claims.
- Keep FastAPI and Redis on private networks.
- Disable debug endpoints.
- Replace console output with centralized structured logs.
- Configure Redis persistence, backup, and high availability according to recovery requirements.
- Add metrics and traces for LLM duration, tool accuracy, provider errors, and GraphQL failures.
- Run unit, integration, and container health tests in CI.

## Troubleshooting

### `401 Missing auth headers` or `Invalid signature`

- Verify the request goes through the Node.js gateway.
- Ensure the Node and Python HMAC secrets match.
- Check system clocks; signatures have a short replay-prevention window.

### `503 All LLM providers...`

- Confirm `GEMINI_API_KEY` or `OPENAI_API_KEY` reaches the AI container.
- Review provider errors in the AI service logs.

### Redis connection errors

- In Compose, use `redis://redis:6379`.
- For local service-by-service development, use the host/port where Redis is running.

### GraphQL connection errors

- In Compose, use the service name rather than `localhost`.
- Confirm the mock server health endpoint and service key configuration.
