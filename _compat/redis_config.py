"""Shim for src.core.shared.redis_config."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.redis_config import *  # noqa: F403
else:
    try:
        from src.core.shared.redis_config import *  # noqa: F403
    except ImportError:

        class RedisConfig:
            url: str = "redis://localhost:6379"
            db: int = 0
            max_connections: int = 10
            socket_timeout: float = 5.0
            decode_responses: bool = True

            def __init__(self, **kwargs: Any) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

        def get_redis_url(db: int = 0) -> str:
            return f"redis://localhost:6379/{db}"

        def get_redis_config() -> RedisConfig:
            return RedisConfig()

        async def get_redis_client(**kwargs: Any) -> None:
            """Stub: returns None in standalone mode (no Redis)."""
            return None
