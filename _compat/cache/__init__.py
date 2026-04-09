"""Shim package for src.core.shared.cache."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache as _lru
from typing import TYPE_CHECKING, Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

if TYPE_CHECKING:
    from src.core.shared.cache import *  # noqa: F403
    from src.core.shared.cache import workflow_cache
else:
    try:
        from src.core.shared import cache as _shared_cache
    except ImportError:
        _shared_cache = None

    if _shared_cache is not None:
        workflow_cache = cast(Any, _shared_cache.workflow_cache)
        __all__ = getattr(_shared_cache, "__all__", ["workflow_cache"])
    else:

        def workflow_cache(
            func: F | None = None,
            *,
            maxsize: int = 128,
            ttl: int | None = None,
        ) -> Callable[[F], F] | F:
            """No-op workflow cache for standalone mode."""
            del ttl
            if func is None:
                return lambda wrapped: cast(F, _lru(maxsize=maxsize)(wrapped))
            return cast(F, _lru(maxsize=maxsize)(func))

        __all__ = ["workflow_cache"]
