import os
import sys
import types
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# Keep unit tests independent from deployed services and live LLM credentials.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("HMAC_SECRET", "test-hmac-secret")
os.environ.setdefault("NODEJS_GRAPHQL_URL", "http://mock.invalid/graphql")
os.environ.setdefault("SERVICE_ACCOUNT_KEY", "test-service-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("USE_LLM_FOR_AGENT_ROUTING", "false")

# Product parsing tests do not call an LLM. Stub the global manager so the
# provider SDKs and API credentials are not required during unit collection.
provider_manager_module = types.ModuleType("providers.manager")
provider_manager_module.provider_manager = object()
sys.modules.setdefault("providers.manager", provider_manager_module)
