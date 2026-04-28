import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock
import os

# Adjust the path for imports based on your project structure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..' )))

from main import app
from core.session_manager import SessionManager
from providers.manager import ProviderManager
from agent.orchestrator import Orchestrator
from config.settings import settings

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.fixture(autouse=True)
def mock_env_vars():
    # Mock environment variables for testing
    os.environ["HMAC_SECRET"] = "test-hmac-secret"
    os.environ["NODEJS_GRAPHQL_URL"] = "http://mock-graphql-server:4010/graphql"
    os.environ["SERVICE_ACCOUNT_KEY"] = "test-service-key"
    os.environ["REDIS_URL"] = "redis://localhost:6379/9" # Use a different Redis DB for tests
    os.environ["WHISPER_MODEL_SIZE"] = "tiny"
    os.environ["DEBUG_ENDPOINTS_ENABLED"] = "true"

    # Re-initialize settings to pick up new env vars
    from config.settings import Settings
    settings.__init__()

@pytest_asyncio.fixture
async def mock_session_manager():
    # Mock Redis client methods
    mock_redis = AsyncMock()
    mock_redis.lrange.return_value = []
    mock_redis.rpush.return_value = None
    mock_redis.ltrim.return_value = None
    mock_redis.expire.return_value = None
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = None
    mock_redis.delete.return_value = None
    mock_redis.ping.return_value = True

    # Patch the session_manager instance with the mock Redis client
    SessionManager.redis_client = mock_redis
    return SessionManager()

@pytest_asyncio.fixture
async def mock_provider_manager():
    # Mock the LLM provider for testing
    mock_provider = AsyncMock()
    mock_provider.name = "mock_provider"
    mock_provider.model = "mock_model"
    mock_provider.supports_tool_calling = True
    mock_provider.complete.return_value = {"content": "Mock AI response", "activeProvider": "mock_provider"}

    mock_manager = MagicMock(spec=ProviderManager)
    mock_manager.providers = [mock_provider]
    mock_manager.complete.return_value = {"content": "Mock AI response", "activeProvider": "mock_provider"}
    mock_manager.get_provider_status.return_value = {"status": "active", "until": None}
    mock_manager.get_current_usage.return_value = 0
    mock_manager.increment_usage.return_value = None
    
    # Patch the global provider_manager instance
    ProviderManager.providers = [mock_provider]
    ProviderManager.complete = mock_manager.complete
    ProviderManager.get_provider_status = mock_manager.get_provider_status
    ProviderManager.get_current_usage = mock_manager.get_current_usage
    ProviderManager.increment_usage = mock_manager.increment_usage

    return mock_manager

@pytest_asyncio.fixture
async def mock_graphql_client():
    mock_client = AsyncMock()
    mock_client.execute_mutation.return_value = {"success": True, "message": "Mock mutation success", "data": {"message": "Mock mutation success"}}
    return mock_client

@pytest_asyncio.fixture(autouse=True)
async def setup_mocks(mock_session_manager, mock_provider_manager, mock_graphql_client):
    # Patch global instances
    from core import session_manager
    session_manager.redis_client = mock_session_manager.redis_client

    from providers import manager
    manager.provider_manager = mock_provider_manager

    from core import graphql_client
    graphql_client.graphql_client = mock_graphql_client

    # Patch orchestrator's domains to use mocked provider manager if needed
    from agent import orchestrator
    orchestrator.orchestrator.provider_manager = mock_provider_manager

    # Mock transcribe_audio if needed
    from core import stt
    stt.transcribe_audio = AsyncMock(return_value="transcribed text")
    stt.load_whisper_model = MagicMock() # Prevent actual model loading during tests
