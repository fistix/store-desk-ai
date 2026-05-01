# Multi-stage Dockerfile - Frontend
# Optimized for both development and production builds

FROM node:18-alpine AS base
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Development stage
FROM base AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production stage
FROM base AS production
RUN npm run build
COPY --from=production /app/dist /app/dist
EXPOSE 3000
CMD ["npm", "start"]
