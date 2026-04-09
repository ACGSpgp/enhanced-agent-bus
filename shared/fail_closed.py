"""Fail-closed decorator for enhanced_agent_bus.

Canonical implementation lives in ``acgs_lite.fail_closed``.  This module
provides a bus-specific superset that also supports:

- **callable deny values** (handler receives ``*args, error=exc``)
- **``exceptions`` kwarg** (alias for the canonical ``reraise`` inverse)

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from importlib import import_module
from typing import TYPE_CHECKING, Any, TypeVar, cast

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from acgs_lite.fail_closed import FailClosedError as ImportedFailClosedError
else:
    try:
        ImportedFailClosedError = import_module("acgs_lite.fail_closed").FailClosedError
    except ModuleNotFoundError as exc:
        if exc.name not in {"acgs_lite", "acgs_lite.fail_closed"}:
            raise
        logger.warning(
            "acgs_lite.fail_closed is unavailable; enhanced_agent_bus is using a local "
            "FailClosedError fallback"
        )
        ImportedFailClosedError = Exception


class FailClosedError(ImportedFailClosedError):
    """Fallback-aware fail-closed exception type."""


__all__ = ["FailClosedError", "fail_closed"]

F = TypeVar("F", bound=Callable[..., Any])


def fail_closed(
    deny_value: Any = None,
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    log_level: int = logging.WARNING,
    message: str = "fail_closed: operation failed, returning deny value",
    reraise: tuple[type[BaseException], ...] = (KeyboardInterrupt, SystemExit),
) -> Callable[[F], F]:
    """Decorator: wraps sync or async functions in fail-closed error handling.

    Extends the canonical ``acgs_lite.fail_closed`` with:

    - **callable deny_value**: if ``deny_value`` is callable it is invoked with
      the original ``*args, **kwargs`` plus ``error=exc``.
    - **exceptions**: tuple of exception types to catch (default ``(Exception,)``).
      Exceptions NOT in this tuple propagate.  ``reraise`` also always propagates.
    """
    deny_handler: Callable[..., Any] | None = deny_value if callable(deny_value) else None

    def decorator(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await fn(*args, **kwargs)
                except reraise:
                    raise
                except exceptions as exc:
                    logger.log(
                        log_level,
                        "%s: %s.%s: %s",
                        message,
                        fn.__module__,
                        fn.__qualname__,
                        type(exc).__name__,
                    )
                    if deny_handler is None:
                        return cast(Any, deny_value)
                    result = deny_handler(*args, **{**kwargs, "error": exc})
                    if inspect.isawaitable(result):
                        awaited_result = await result
                        return cast(Any, awaited_result)
                    return cast(Any, result)

            return cast(F, async_wrapper)
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return fn(*args, **kwargs)
                except reraise:
                    raise
                except exceptions as exc:
                    logger.log(
                        log_level,
                        "%s: %s.%s: %s",
                        message,
                        fn.__module__,
                        fn.__qualname__,
                        type(exc).__name__,
                    )
                    if deny_handler is None:
                        return cast(Any, deny_value)
                    return cast(Any, deny_handler(*args, **{**kwargs, "error": exc}))

            return cast(F, sync_wrapper)

    return decorator
