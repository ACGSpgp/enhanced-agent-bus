"""
ACGS-2 Circuit Breaker Decorator

Constitutional Hash: 608508a9bd224290

This module provides the with_service_circuit_breaker decorator for wrapping
async functions with circuit breaker protection.
"""

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Protocol, TypeVar, cast

try:
    from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "standalone"

from enhanced_agent_bus.observability.structured_logging import get_logger

from .config import ServiceCircuitConfig
from .enums import CircuitState, FallbackStrategy, ServiceSeverity
from .exceptions import CircuitBreakerOpen
from .registry import get_service_circuit_breaker

logger = get_logger(__name__)
SERVICE_CIRCUIT_EXECUTION_ERRORS = (
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    ConnectionError,
    OSError,
    asyncio.TimeoutError,
)

T = TypeVar("T")


class _CircuitBreakerConfigProtocol(Protocol):
    fallback_strategy: FallbackStrategy
    severity: ServiceSeverity


class _ServiceCircuitBreakerProtocol(Protocol):
    config: _CircuitBreakerConfigProtocol
    state: CircuitState

    async def can_execute(self) -> bool: ...
    async def record_rejection(self) -> None: ...
    async def record_success(self) -> None: ...
    async def record_failure(self, error: Exception | None = None, error_type: str = "unknown") -> None: ...
    def get_cached_fallback(self, key: str) -> object | None: ...
    async def queue_for_retry(
        self, request_id: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> bool: ...
    def set_cached_fallback(self, key: str, value: object) -> None: ...


AsyncFunc = Callable[..., Awaitable[T]]


def _fallback_cache_key(cache_key: str | None, service_name: str) -> str:
    """Resolve fallback cache key with service-level default."""
    return cache_key or service_name


def _raise_circuit_open(service_name: str, message: str, strategy: FallbackStrategy) -> None:
    """Raise canonical circuit-open exception."""
    raise CircuitBreakerOpen(service_name, message, strategy.value)


def _handle_cached_value_strategy(
    cb: _ServiceCircuitBreakerProtocol,
    service_name: str,
    cache_key: str | None,
) -> object:
    """Handle CACHED_VALUE fallback behavior."""
    cached = cb.get_cached_fallback(_fallback_cache_key(cache_key, service_name))
    if cached is not None:
        logger.info(f"[{CONSTITUTIONAL_HASH}] Using cached fallback for {service_name}")
        return cached
    _raise_circuit_open(service_name, "No cached fallback available", cb.config.fallback_strategy)
    raise AssertionError("unreachable")


async def _handle_queue_for_retry_strategy(
    cb: _ServiceCircuitBreakerProtocol,
    service_name: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> object | None:
    """Handle QUEUE_FOR_RETRY fallback behavior."""
    import uuid

    request_id = str(uuid.uuid4())
    queued = await cb.queue_for_retry(request_id, args, kwargs)
    if queued:
        logger.info(f"[{CONSTITUTIONAL_HASH}] Request queued for retry ({service_name})")

    if cb.config.severity == ServiceSeverity.CRITICAL:
        _raise_circuit_open(
            service_name,
            "Request queued but critical service unavailable",
            cb.config.fallback_strategy,
        )
    return None


async def _handle_open_circuit(
    cb: _ServiceCircuitBreakerProtocol,
    service_name: str,
    fallback_value: object | None,
    cache_key: str | None,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> object:
    """Apply configured fallback strategy when circuit is open."""
    strategy = cb.config.fallback_strategy

    if strategy == FallbackStrategy.FAIL_CLOSED:
        _raise_circuit_open(
            service_name, f"Service unavailable, circuit is {cb.state.value}", strategy
        )

    if strategy == FallbackStrategy.CACHED_VALUE:
        return _handle_cached_value_strategy(cb, service_name, cache_key)

    if strategy == FallbackStrategy.QUEUE_FOR_RETRY:
        return await _handle_queue_for_retry_strategy(cb, service_name, args, kwargs)

    if strategy == FallbackStrategy.BYPASS:
        logger.info(f"[{CONSTITUTIONAL_HASH}] Bypassing {service_name} (circuit open)")
        return fallback_value

    if strategy == FallbackStrategy.DEFAULT_VALUE:
        return fallback_value

    _raise_circuit_open(service_name, "Unsupported fallback strategy", strategy)
    raise AssertionError("unreachable")


def _cache_successful_result(
    cb: _ServiceCircuitBreakerProtocol,
    cache_key: str | None,
    service_name: str,
    result: object,
) -> None:
    """Cache successful result when CACHED_VALUE strategy is enabled."""
    if cb.config.fallback_strategy != FallbackStrategy.CACHED_VALUE or result is None:
        return
    cb.set_cached_fallback(_fallback_cache_key(cache_key, service_name), result)


def with_service_circuit_breaker(
    service_name: str,
    fallback_value: object | None = None,
    cache_key: str | None = None,
    config: ServiceCircuitConfig | None = None,
) -> Callable[[AsyncFunc[T]], AsyncFunc[T]]:
    """
    Decorator to wrap a function with service-specific circuit breaker.

    Args:
        service_name: Name of the service for the circuit breaker
        fallback_value: Value to return when using DEFAULT_VALUE strategy
        cache_key: Key for cached fallback (CACHED_VALUE strategy)
        config: Optional custom circuit breaker configuration

    Usage:
        @with_service_circuit_breaker('policy_registry', cache_key='policies')
        async def get_policies():
            ...
    """

    def decorator(func: AsyncFunc[T]) -> AsyncFunc[T]:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            cb = cast(
                _ServiceCircuitBreakerProtocol,
                await get_service_circuit_breaker(service_name, config),
            )

            if not await cb.can_execute():
                await cb.record_rejection()
                fallback_result = await _handle_open_circuit(
                    cb=cb,
                    service_name=service_name,
                    fallback_value=fallback_value,
                    cache_key=cache_key,
                    args=args,
                    kwargs=kwargs,
                )
                return cast(T, fallback_result)

            try:
                result = await func(*args, **kwargs)
                await cb.record_success()
                _cache_successful_result(cb, cache_key, service_name, result)
                return result

            except Exception as e:
                # Circuit breaker MUST catch all exceptions from the wrapped
                # service — including domain-specific errors not in the named
                # tuple (e.g. OPAFailureError, KafkaProducerError). Narrowing
                # this catch causes those errors to bypass failure recording
                # so the circuit never opens for them.
                await cb.record_failure(e, type(e).__name__)
                raise

        return cast(AsyncFunc[T], wrapper)

    return decorator


__all__ = [
    "with_service_circuit_breaker",
]
