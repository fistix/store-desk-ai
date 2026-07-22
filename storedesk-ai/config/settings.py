import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    DEBUG_ENDPOINTS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    HMAC_SECRET: str
    NODEJS_GRAPHQL_URL: str
    SERVICE_ACCOUNT_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # LLM Providers
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # STT
    WHISPER_MODEL_SIZE: str = "base"

    # Limits
    SESSION_TTL_SECONDS: int = 7200
    MAX_HISTORY_TURNS: int = 20
    PROVIDER_BACKOFF_SECONDS: int = 300
    REQUEST_MAX_ITERATIONS: int = 1 #5
    # AI-side rate limit (defense in depth behind the Node gateway)
    RATE_LIMIT_PER_USER: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    class Config:
        env_file = ".env.production" if os.getenv("ENVIRONMENT") == "production" else ".env"

settings = Settings()
