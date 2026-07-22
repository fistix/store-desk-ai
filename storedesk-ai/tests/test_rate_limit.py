"""Unit tests for fixed-window Redis rate limiting."""

import asyncio
from unittest.mock import AsyncMock, patch

from security.redis_security_manager import RedisSecurityManager


def test_fixed_window_sets_expire_only_on_new_key():
    manager = RedisSecurityManager()
    eval_mock = AsyncMock(side_effect=[
        [1, 60],  # first request: create window
        [2, 55],  # second request: same window, TTL not reset by caller
        [3, 50],  # third: still under limit=3
        [4, 45],  # fourth: over limit
    ])

    with patch("security.redis_security_manager.redis_client") as redis_mock:
        redis_mock.eval = eval_mock
        limited1, retry1 = asyncio.run(
            manager.is_rate_limited("user-a", "input_validation", limit=3, window_seconds=60)
        )
        limited2, _ = asyncio.run(
            manager.is_rate_limited("user-a", "input_validation", limit=3, window_seconds=60)
        )
        limited3, _ = asyncio.run(
            manager.is_rate_limited("user-a", "input_validation", limit=3, window_seconds=60)
        )
        limited4, retry4 = asyncio.run(
            manager.is_rate_limited("user-a", "input_validation", limit=3, window_seconds=60)
        )

    assert (limited1, retry1) == (False, 0)
    assert limited2 is False
    assert limited3 is False
    assert limited4 is True
    assert retry4 == 45

    # Lua script must be used (atomic INCR + conditional EXPIRE)
    assert eval_mock.await_count == 4
    script = eval_mock.await_args_list[0].args[0]
    assert "INCR" in script
    assert "EXPIRE" in script
    assert "TTL" in script


def test_rate_limit_fail_open_on_redis_error():
    manager = RedisSecurityManager()
    with patch("security.redis_security_manager.redis_client") as redis_mock:
        redis_mock.eval = AsyncMock(side_effect=ConnectionError("redis down"))
        limited, retry = asyncio.run(
            manager.is_rate_limited("user-b", "input_validation", limit=1, window_seconds=60)
        )

    assert limited is False
    assert retry == 0
