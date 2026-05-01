# Multi-stage Dockerfile - StoreDesk AI
# Optimized for both development and production builds

FROM python:3.9-slim AS base
WORKDIR /app

# Create cache directory for pip packages
RUN mkdir -p /root/.cache/pip

# Install system dependencies for all stages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    python3-dev \
    build-essential \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --cache-dir /root/.cache/pip --timeout 600 --retries 3 -r requirements.txt

# Development stage
FROM base AS development
RUN pip install uvicorn[standard] pytest black flake8
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app", "--log-level", "debug"]

# Production stage
FROM base AS production
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
