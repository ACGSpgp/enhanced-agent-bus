"""Shim for ``src.core.shared.acgs_logging``."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeAlias, cast

from starlette.requests import Request
from starlette.responses import Response


class _FallbackStructuredLogger:
    """Minimal structured logger fallback."""

    def __init__(self, name: str, service: str, json_format: bool = True) -> None:
        self.name = name
        self.service = service
        self.json_format = json_format
        self._logger = logging.getLogger(name)

    def info(self, event: str, **kwargs: object) -> None:
        self._logger.info(event, extra=kwargs or None)

    def warning(self, event: str, **kwargs: object) -> None:
        self._logger.warning(event, extra=kwargs or None)

    def error(self, event: str, **kwargs: object) -> None:
        self._logger.error(event, extra=kwargs or None)

    def debug(self, event: str, **kwargs: object) -> None:
        self._logger.debug(event, extra=kwargs or None)


_CorrelationMiddleware: TypeAlias = Callable[
    [Request, Callable[[Request], Awaitable[Response]]],
    Awaitable[Response],
]


class _SharedLoggingModule(Protocol):
    StructuredLogger: type[_FallbackStructuredLogger]

    def get_logger(self, name: str | None = None) -> logging.Logger: ...

    def init_service_logging(
        self,
        service_name: str,
        level: str = "INFO",
        json_format: bool = True,
    ) -> _FallbackStructuredLogger: ...

    def create_correlation_middleware(self) -> _CorrelationMiddleware: ...


try:
    from src.core.shared import acgs_logging as _shared_acgs_logging_module
except ImportError:
    _shared_acgs_logging: _SharedLoggingModule | None = None
else:
    _shared_acgs_logging = cast(_SharedLoggingModule, _shared_acgs_logging_module)


StructuredLogger = (
    _shared_acgs_logging.StructuredLogger
    if _shared_acgs_logging is not None
    else _FallbackStructuredLogger
)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the shared logger helper or a stdlib fallback."""
    if _shared_acgs_logging is not None:
        return _shared_acgs_logging.get_logger(name)
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def init_service_logging(
    service_name: str,
    level: str = "INFO",
    json_format: bool = True,
) -> _FallbackStructuredLogger:
    """Configure basic logging for standalone mode or delegate to shared logging."""
    if _shared_acgs_logging is not None:
        return _shared_acgs_logging.init_service_logging(service_name, level, json_format)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return _FallbackStructuredLogger(service_name, service_name, json_format)


def create_correlation_middleware() -> _CorrelationMiddleware:
    """Return the shared correlation middleware or a pass-through fallback."""
    if _shared_acgs_logging is not None:
        return _shared_acgs_logging.create_correlation_middleware()

    async def correlation_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        return await call_next(request)

    return correlation_middleware


__all__ = [
    "StructuredLogger",
    "create_correlation_middleware",
    "get_logger",
    "init_service_logging",
]
