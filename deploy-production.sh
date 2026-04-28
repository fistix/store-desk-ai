#!/bin/bash

# Production Deployment Script
# Usage: ./deploy-production.sh

set -e

echo "🚀 Starting StoreDesk AI Production Deployment..."

# Check if production env file exists
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "Please copy .env.production.example to .env.production and configure your secrets."
    exit 1
fi

# Check if required variables are set
source .env.production

if [ -z "$STOREDESK_AI_HMAC_SECRET" ] || [ -z "$HMAC_SECRET" ]; then
    echo "❌ Required security variables not set in .env.production"
    exit 1
fi

echo "✅ Environment variables validated"

# Build production images
echo "🔨 Building production Docker images..."
docker-compose -f docker-compose.prod.yml --env-file .env.production build

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production down || true

# Start production services
echo "🚀 Starting production services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
for service in nodejs storedesk-ai redis frontend; do
    if docker-compose -f docker-compose.prod.yml --env-file .env.production ps $service | grep -q "Up (healthy)"; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not healthy"
        docker-compose -f docker-compose.prod.yml --env-file .env.production logs $service
        exit 1
    fi
done

echo "🎉 StoreDesk AI deployed successfully!"
echo "📊 Service status:"
docker-compose -f docker-compose.prod.yml --env-file .env.production ps

echo "🌐 Access the application at:"
echo "   Frontend: http://localhost:3000/storedesk-test"
echo "   Backend API: http://localhost:4010/api/storedesk/assist"
echo "   Health Checks: http://localhost:4010/health"
