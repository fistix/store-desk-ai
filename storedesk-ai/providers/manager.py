import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from fastapi import HTTPException

from config.settings import settings
from providers.base import LLMProvider
from providers.gemini import GeminiProvider
from providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Load supported LLMs and fail over between healthy providers."""

    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self._load_providers()

    def _load_providers(self) -> None:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            self.providers.append(
                GeminiProvider("gemini", "gemini-2.5-flash", gemini_key)
            )

        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.providers.append(
                OpenAIProvider("openai", "gpt-4o-mini", openai_key)
            )

        if self.providers:
            logger.info(
                "Loaded %d LLM provider(s): %s",
                len(self.providers),
                ", ".join(provider.name for provider in self.providers),
            )
        else:
            logger.error(
                "No LLM provider loaded. Set GEMINI_API_KEY or OPENAI_API_KEY "
                "in the service environment (e.g. .env.dev / .env.production)."
            )

    async def _get_usage_key(self, provider_name: str) -> str:
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"provider_usage:{provider_name}:{today_utc}"

    async def _get_status_key(self, provider_name: str) -> str:
        return f"provider_status:{provider_name}"

    async def get_provider_status(self, provider_name: str) -> Dict[str, Any]:
        status_json = await self.redis_client.get(
            await self._get_status_key(provider_name)
        )
        if status_json:
            return json.loads(status_json)
        return {"status": "active", "until": None}

    async def set_provider_backoff(self, provider_name: str, seconds: int) -> None:
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        status_data = {"status": "backoff", "until": until.isoformat()}
        await self.redis_client.setex(
            await self._get_status_key(provider_name),
            seconds,
            json.dumps(status_data),
        )

    async def increment_usage(self, provider_name: str) -> None:
        usage_key = await self._get_usage_key(provider_name)
        await self.redis_client.incr(usage_key)

        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await self.redis_client.expireat(usage_key, int(next_midnight.timestamp()))

    async def get_current_usage(self, provider_name: str) -> int:
        usage = await self.redis_client.get(
            await self._get_usage_key(provider_name)
        )
        return int(usage) if usage else 0

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.providers:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No LLM provider is configured. Set GEMINI_API_KEY or "
                    "OPENAI_API_KEY in the service environment."
                ),
            )

        last_error: Optional[str] = None

        for provider in self.providers:
            try:
                status = await self.get_provider_status(provider.name)
                if status.get("status") == "backoff":
                    logger.info("Skipping provider %s during backoff", provider.name)
                    last_error = f"{provider.name}: in backoff"
                    continue
            except Exception as exc:
                # Redis telemetry should not prevent an otherwise valid LLM call.
                logger.warning(
                    "Could not read status for provider %s: %s",
                    provider.name,
                    exc,
                )

            started_at = time.monotonic()
            try:
                response = await provider.complete(messages, tools)
                if not isinstance(response, dict):
                    raise TypeError("Provider response must be a dictionary")

                duration_ms = (time.monotonic() - started_at) * 1000
                response["activeProvider"] = provider.name
                response["providerDuration"] = duration_ms

                try:
                    await self.increment_usage(provider.name)
                except Exception as exc:
                    logger.warning(
                        "Could not record usage for provider %s: %s",
                        provider.name,
                        exc,
                    )

                logger.info(
                    "Provider %s completed request in %.2f ms",
                    provider.name,
                    duration_ms,
                )
                return response
            except Exception as exc:
                last_error = f"{provider.name}: {exc!r}"
                logger.warning(
                    "Provider %s failed: %r", provider.name, exc, exc_info=True
                )
                try:
                    await self.set_provider_backoff(
                        provider.name,
                        settings.PROVIDER_BACKOFF_SECONDS,
                    )
                except Exception as backoff_exc:
                    logger.warning(
                        "Could not record backoff for provider %s: %s",
                        provider.name,
                        backoff_exc,
                    )

        detail = "All configured LLM providers are unavailable."
        if last_error:
            detail = f"{detail} Last error: {last_error}"
        logger.error(detail)
        raise HTTPException(status_code=503, detail=detail)


provider_manager = ProviderManager()
