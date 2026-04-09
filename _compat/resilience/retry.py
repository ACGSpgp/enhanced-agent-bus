"""Shim for src.core.shared.resilience.retry."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from src.core.shared.resilience.retry import RetryConfig, retry
else:
    try:
        from src.core.shared.resilience.retry import *  # noqa: F403
    except ImportError:
        F = TypeVar("F", bound=Callable[..., Any])

        class RetryConfig:
            max_retries: int = 3
            max_attempts: int | None = None
            base_delay: float = 1.0
            max_delay: float = 60.0
            multiplier: float = 2.0
            jitter: bool = True
            jitter_factor: float = 0.25
            retryable_exceptions: tuple[type[BaseException], ...] = (Exception,)
            on_retry: Callable[[int, BaseException], None] | None = None
            raise_on_exhausted: bool = True

            def __init__(self, **kwargs: Any) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

        def retry(
            max_retries: int | None = None,
            max_attempts: int | None = None,
            base_delay: float | None = None,
            max_delay: float | None = None,
            retryable_exceptions: tuple[type[BaseException], ...] | None = None,
            on_retry: Callable[[int, BaseException], None] | None = None,
            config: RetryConfig | None = None,
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            """No-op retry decorator — calls the function once without retries."""

            def decorator(fn: F) -> F:
                @functools.wraps(fn)
                def wrapper(*args: Any, **kw: Any) -> Any:
                    return fn(*args, **kw)

                @functools.wraps(fn)
                async def async_wrapper(*args: Any, **kw: Any) -> Any:
                    return await fn(*args, **kw)

                import asyncio

                if asyncio.iscoroutinefunction(fn):
                    return async_wrapper  # type: ignore[return-value]
                return wrapper  # type: ignore[return-value]

            return decorator

        async def retry_async(
            fn: Callable[..., Any],
            *args: Any,
            config: RetryConfig | None = None,
            **kwargs: Any,
        ) -> Any:
            """Stub: calls fn once without retries."""
            return await fn(*args, **kwargs)

__all__ = ["RetryConfig", "retry", "retry_async"]
