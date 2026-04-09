"""Shim for src.core.shared.security.error_sanitizer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

_shared_error_sanitizer: Any | None = None
try:
    from src.core.shared.security import error_sanitizer as _shared_error_sanitizer_module
except ImportError:
    pass
else:
    _shared_error_sanitizer = _shared_error_sanitizer_module

if _shared_error_sanitizer is not None:
    sanitize_error = cast(
        Callable[[Exception | str | None], str],
        _shared_error_sanitizer.sanitize_error,
    )
    safe_error_detail = cast(
        Callable[[Exception | str | None, str], str],
        _shared_error_sanitizer.safe_error_detail,
    )
    # sanitize_error_message and safe_error_response are shim-local names defined below.
else:

    def sanitize_error(error: Exception | str | None) -> str:
        """Return only the exception type name or a generic safe label."""
        if isinstance(error, BaseException):
            return type(error).__name__
        if isinstance(error, str) and error:
            return "Error"
        return "UnknownError"

    def safe_error_detail(error: Exception | str | None, operation: str = "operation") -> str:
        del operation
        return sanitize_error(error)


def sanitize_error_message(message: str) -> str:
    del message
    return "An internal error occurred."


def safe_error_response(exc: Exception | str | None) -> dict[str, str]:
    return {
        "error": sanitize_error(exc),
        "message": "An internal error occurred.",
    }


__all__ = [
    "safe_error_detail",
    "safe_error_response",
    "sanitize_error",
    "sanitize_error_message",
]
