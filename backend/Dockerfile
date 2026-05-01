# Multi-stage Dockerfile - NodeJS Backend
# Optimized for both development and production builds

FROM node:18-alpine AS base
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Development stage
FROM base AS development
RUN npm install -g nodemon
COPY . .
EXPOSE 4010
CMD ["nodemon", "app.js"]

# Production stage
FROM base AS production
COPY . .
EXPOSE 4010
CMD ["node", "app.js"]
