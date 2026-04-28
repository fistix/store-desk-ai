# Quick Start Guide

## Development Setup

```bash
# 1. Clone and setup
git clone <repository>
cd store-desk-ai

# 2. Configure environment
cp backend/.env.example backend/.env
cp storedesk-mock-server/.env.example storedesk-mock-server/.env
cp storedesk-ai/.env.example storedesk-ai/.env
cp frontend/.env.example frontend/.env

# 3. Start development with hot reloading
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 4. Access test interface
# http://localhost:3000/storedesk-test
```

## Production Deployment

```bash
# 1. Configure production environment
cp .env.production.example .env.production
# Edit .env.production with your actual secrets

# 2. Deploy to production
./deploy-production.sh

# Or manually:
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## Key Commands

```bash
# Development (with hot reloading)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production (no source mounting)
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache
```

## Required Environment Variables

### Development
- `STOREDESK_AI_HMAC_SECRET` (any string)
- `STOREDESK_AI_SERVICE_KEY` (hash of service key)
- `GEMINI_API_KEY` (for AI functionality)

### Production
- Same as development + production-specific settings
- See `.env.production.example` for full list
