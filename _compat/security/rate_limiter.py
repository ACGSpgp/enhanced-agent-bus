"""Shim for src.core.shared.security.rate_limiter."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from fastapi import Request
    from src.core.shared.security.rate_limiter import (  # noqa: F401
        RateLimiter,
        RateLimitMiddleware,
        _extract_request_from_call,
        _module_available,
        _parse_bool_env,
        _resolve_rate_limit_identifier,
        add_rate_limit_headers,
        configure_rate_limits,
        create_rate_limit_middleware,
        rate_limit,
        update_rate_limit_metrics,
    )
else:
    try:
        from src.core.shared.security import rate_limiter as _shared_rate_limiter
    except ImportError:
        _shared_rate_limiter = None

    if _shared_rate_limiter is not None:
        RateLimitMiddleware = _shared_rate_limiter.RateLimitMiddleware
        RateLimiter = _shared_rate_limiter.RateLimiter
        SlidingWindowRateLimiter = _shared_rate_limiter.SlidingWindowRateLimiter
        RateLimitRule = _shared_rate_limiter.RateLimitRule
        RateLimitScope = _shared_rate_limiter.RateLimitScope
        RateLimitAlgorithm = _shared_rate_limiter.RateLimitAlgorithm
        RateLimitResult = _shared_rate_limiter.RateLimitResult
        RateLimitConfig = _shared_rate_limiter.RateLimitConfig
        rate_limiter = _shared_rate_limiter.rate_limiter
        TenantQuota = _shared_rate_limiter.TenantQuota
        TenantRateLimitProvider = _shared_rate_limiter.TenantRateLimitProvider
        TokenBucket = _shared_rate_limiter.TokenBucket
        _extract_request_from_call = _shared_rate_limiter._extract_request_from_call
        _module_available = _shared_rate_limiter._module_available
        _parse_bool_env = _shared_rate_limiter._parse_bool_env
        _resolve_rate_limit_identifier = _shared_rate_limiter._resolve_rate_limit_identifier
        add_rate_limit_headers = _shared_rate_limiter.add_rate_limit_headers
        configure_rate_limits = _shared_rate_limiter.configure_rate_limits
        create_rate_limit_middleware = _shared_rate_limiter.create_rate_limit_middleware
        rate_limit = _shared_rate_limiter.rate_limit
        update_rate_limit_metrics = _shared_rate_limiter.update_rate_limit_metrics
        __all__ = getattr(
            _shared_rate_limiter,
            "__all__",
            [
                "RateLimitAlgorithm",
                "RateLimitConfig",
                "RateLimitMiddleware",
                "RateLimitResult",
                "RateLimitRule",
                "RateLimitScope",
                "RateLimiter",
                "SlidingWindowRateLimiter",
                "TenantQuota",
                "TenantRateLimitProvider",
                "TokenBucket",
                "_extract_request_from_call",
                "_module_available",
                "_parse_bool_env",
                "_resolve_rate_limit_identifier",
                "add_rate_limit_headers",
                "configure_rate_limits",
                "create_rate_limit_middleware",
                "rate_limit",
                "update_rate_limit_metrics",
            ],
        )
    else:
        try:
            from fastapi import Request
        except ImportError:
            Request = Any  # type: ignore[assignment,misc]

        class RateLimiter:
            """No-op rate limiter for standalone mode."""

            def __init__(
                self,
                redis_client: object | None = None,
                default_requests_per_minute: int = 60,
                default_burst_limit: int = 120,
            ) -> None:
                del redis_client
                self.default_requests_per_minute = default_requests_per_minute
                self.default_burst_limit = default_burst_limit

            async def check(self, key: str) -> bool:
                del key
                return True

            async def is_allowed(self, key: str) -> bool:
                del key
                return True

            async def reset(self, key: str) -> None:
                del key

        # Alias so imports of SlidingWindowRateLimiter work in standalone mode
        SlidingWindowRateLimiter = RateLimiter

        class RateLimitMiddleware:
            """No-op middleware stub."""

            def __init__(self, app: object = None, **kwargs: object) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(self, scope: object, receive: object, send: object) -> None:
                if callable(self.app):
                    await cast(
                        Callable[[object, object, object], Awaitable[None]],
                        self.app,
                    )(scope, receive, send)

        def _parse_bool_env(value: str | None) -> bool | None:
            """Parse a boolean-ish environment variable string."""
            if value is None:
                return None
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            return None

        def _module_available(module_name: str) -> bool:
            """Return whether a module is available without crashing on stub modules."""
            try:
                return importlib.util.find_spec(module_name) is not None
            except (ModuleNotFoundError, ValueError):
                return sys.modules.get(module_name) is not None

        def _extract_request_from_call(
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> Request | None:
            """Extract FastAPI Request from decorated endpoint call."""
            request_type = Request if Request is not Any else None
            if request_type is not None:
                for arg in args:
                    if isinstance(arg, request_type):
                        return arg
                request_candidate = kwargs.get("request")
                if isinstance(request_candidate, request_type):
                    return request_candidate
            return None

        def _resolve_rate_limit_identifier(
            request: Request,
            limit_type: str,
            key_func: Callable[[Request], str] | None,
        ) -> str:
            """Resolve the identifier used for scoped rate limiting."""
            if key_func:
                return key_func(request)
            client = getattr(request, "client", None)
            client_ip = getattr(client, "host", "unknown") if client is not None else "unknown"
            if limit_type == "user":
                state = getattr(request, "state", None)
                user_id = getattr(state, "user_id", None)
                return str(user_id) if user_id is not None else client_ip
            if limit_type == "ip":
                return client_ip
            if limit_type == "endpoint":
                url = getattr(request, "url", None)
                path = getattr(url, "path", None)
                return str(path) if path is not None else "unknown"
            return "global"

        def rate_limit(
            requests_per_minute: int = 60,
            burst_limit: int = 120,
            limit_type: str = "ip",
            key_func: Callable[[Request], str] | None = None,
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            """No-op rate limit decorator for standalone mode."""
            del requests_per_minute, burst_limit, limit_type, key_func

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn

            return decorator

        def update_rate_limit_metrics(
            limit_type: str,
            identifier: str,
            endpoint: str,
            allowed: bool,
        ) -> None:
            del limit_type, identifier, endpoint, allowed

        def configure_rate_limits(
            redis_client: object | None = None,
            default_requests_per_minute: int = 60,
            default_burst_limit: int = 120,
        ) -> None:
            del redis_client, default_requests_per_minute, default_burst_limit

        def add_rate_limit_headers() -> Callable[..., Any]:
            """Return a pass-through decorator used by response hooks."""

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn

            return decorator

        def create_rate_limit_middleware(
            requests_per_minute: int = 60,
            burst_limit: int = 120,
            burst_multiplier: float = 2.0,
            fail_open: bool = True,
        ) -> Callable[[object], RateLimitMiddleware]:
            """Factory for no-op middleware."""
            del requests_per_minute, burst_limit, burst_multiplier, fail_open

            def factory(app: object) -> RateLimitMiddleware:
                return RateLimitMiddleware(app=app)

            return factory

        __all__ = [
            "RateLimitMiddleware",
            "RateLimiter",
            "SlidingWindowRateLimiter",
            "_extract_request_from_call",
            "_module_available",
            "_parse_bool_env",
            "_resolve_rate_limit_identifier",
            "add_rate_limit_headers",
            "configure_rate_limits",
            "create_rate_limit_middleware",
            "rate_limit",
            "update_rate_limit_metrics",
        ]
