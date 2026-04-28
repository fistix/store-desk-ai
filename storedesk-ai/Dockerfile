FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env file if it doesn't exist
RUN if [ ! -f .env ]; then \
    echo "PORT=8000" > .env && \
    echo "ENVIRONMENT=development" >> .env && \
    echo "REDIS_URL=redis://localhost:6379" >> .env; \
  fi

EXPOSE 8000

# Install uvicorn for development hot reloading
RUN pip install uvicorn[standard]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
