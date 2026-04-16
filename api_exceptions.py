"""
ACGS-2 Enhanced Agent Bus API Exception Handlers
Exception handlers and middleware for the Enhanced Agent Bus API
Constitutional Hash: 608508a9bd224290

This module contains all exception handlers and error response utilities
extracted from api.py for better code organization and maintainability.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from fastapi import FastAPI, Request, WebSocket, status
from fastapi.responses import JSONResponse, Response

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict
else:
    JSONDict: TypeAlias = dict[str, Any]

from enhanced_agent_bus.observability.structured_logging import get_logger


def _load_init_service_logging() -> Callable[..., Any] | None:
    try:
        return cast(
            Callable[..., Any],
            import_module("enhanced_agent_bus._compat.acgs_logging").init_service_logging,
        )
    except Exception:
        return None


init_service_logging = _load_init_service_logging()

logger: Any
if init_service_logging is not None:
    logger = init_service_logging("enhanced-agent-bus", level="INFO", json_format=True)
else:
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)
    logger = get_logger(__name__)

try:
    _exceptions_module = import_module(".exceptions", __package__)
except (ImportError, ValueError):
    try:
        _exceptions_module = import_module("exceptions")
    except (ImportError, ValueError):
        _exceptions_module = import_module(".fallback_stubs", __package__)

try:
    _ImportedRateLimitExceeded = cast(type[Any], import_module("slowapi.errors").RateLimitExceeded)
except Exception:
    _ImportedRateLimitExceeded = cast(
        type[Any], import_module(".fallback_stubs", __package__).RateLimitExceeded
    )

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="unknown")

RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RateLimitExceededType = cast(type[Exception], _ImportedRateLimitExceeded)
RateLimitExceeded = RateLimitExceededType
MessageTimeoutErrorType = cast(type[Exception], _exceptions_module.MessageTimeoutError)
MessageTimeoutError = MessageTimeoutErrorType
BusNotStartedErrorType = cast(type[Exception], _exceptions_module.BusNotStartedError)
BusNotStartedError = BusNotStartedErrorType
OPAConnectionErrorType = cast(type[Exception], _exceptions_module.OPAConnectionError)
OPAConnectionError = OPAConnectionErrorType
ConstitutionalErrorType = cast(type[Exception], _exceptions_module.ConstitutionalError)
ConstitutionalError = ConstitutionalErrorType
MACIErrorType = cast(type[Exception], _exceptions_module.MACIError)
MACIError = MACIErrorType
PolicyErrorType = cast(type[Exception], _exceptions_module.PolicyError)
PolicyError = PolicyErrorType
AgentErrorType = cast(type[Exception], _exceptions_module.AgentError)
AgentError = AgentErrorType
MessageErrorType = cast(type[Exception], _exceptions_module.MessageError)
MessageError = MessageErrorType
BusOperationErrorType = cast(type[Exception], _exceptions_module.BusOperationError)
BusOperationError = BusOperationErrorType
AgentBusErrorType = cast(type[Exception], _exceptions_module.AgentBusError)
AgentBusError = AgentBusErrorType


def _rate_limit_retry_after_ms(exc: Exception) -> int | None:
    value = getattr(exc, "retry_after_ms", None)
    return value if isinstance(value, int) else None


def _rate_limit_agent_id(exc: Exception) -> str:
    value = getattr(exc, "agent_id", "")
    return value if isinstance(value, str) else ""


def _exception_message(exc: Exception) -> str:
    value = getattr(exc, "message", None)
    return value if isinstance(value, str) and value else str(exc)


def _message_id(exc: Exception) -> str:
    value = getattr(exc, "message_id", "")
    return value if isinstance(value, str) else ""


def _operation(exc: Exception) -> str:
    value = getattr(exc, "operation", "")
    return value if isinstance(value, str) else ""


_ExceptionHandler: TypeAlias = Callable[
    [Request, Exception],
    Response | Awaitable[Response],
]
_WebSocketExceptionHandler: TypeAlias = Callable[[WebSocket, Exception], Awaitable[None]]
_Handler: TypeAlias = _ExceptionHandler | _WebSocketExceptionHandler


def create_error_response(
    exc: Exception, _status_code: int, request_id: str | None = None
) -> JSONDict:
    """Helper to create standardized error responses."""
    return {
        "status": "error",
        "code": getattr(exc, "code", getattr(exc, "error_code", "INTERNAL_ERROR")),
        "message": str(exc),
        "details": getattr(exc, "details", {}),
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle rate limit exceeded errors with 429 status and RFC 6585 rate limit headers."""
    status_code = 429
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )

    # Calculate reset time as epoch timestamp (seconds since Unix epoch)
    retry_after_ms = _rate_limit_retry_after_ms(exc)
    reset_seconds = retry_after_ms // 1000 if retry_after_ms else 60
    reset_epoch = int(datetime.now(UTC).timestamp()) + reset_seconds

    # RFC 6585 rate limit headers
    headers = {
        "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS_PER_MINUTE),
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(reset_epoch),
        "Retry-After": str(reset_seconds),
    }

    logger.warning(
        f"Rate limit exceeded for agent '{_rate_limit_agent_id(exc)}': {_exception_message(exc)}"
    )
    return JSONResponse(status_code=status_code, content=response, headers=headers)


async def message_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle message timeout errors with 504 status."""
    status_code = 504
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Message timeout for '{_message_id(exc)}': {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def bus_not_started_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle bus not started errors with 503 status."""
    status_code = 503
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Bus not started for operation '{_operation(exc)}': {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def opa_connection_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle OPA connection errors with 503 status."""
    status_code = 503
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"OPA connection error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def constitutional_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle constitutional validation errors with 400 status."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Constitutional error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def maci_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle MACI role separation errors."""
    status_code = 403
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"MACI error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def policy_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle policy evaluation errors."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Policy error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def agent_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle agent-related errors."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Agent error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def message_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle message-related errors."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Message error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def bus_operation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle bus operation errors with 503 status."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Bus operation error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def agent_bus_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic AgentBusError (catch-all for bus errors)."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Agent bus error: {_exception_message(exc)}")
    return JSONResponse(status_code=status_code, content=response)


async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with structured error response."""
    correlation_id = correlation_id_var.get()
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add correlation ID to all requests for distributed tracing."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    correlation_id_var.set(correlation_id)

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RateLimitExceededType, cast(_Handler, rate_limit_exceeded_handler))
    app.add_exception_handler(MessageTimeoutErrorType, cast(_Handler, message_timeout_handler))
    app.add_exception_handler(BusNotStartedErrorType, cast(_Handler, bus_not_started_handler))
    app.add_exception_handler(OPAConnectionErrorType, cast(_Handler, opa_connection_handler))
    app.add_exception_handler(
        ConstitutionalErrorType,
        cast(_Handler, constitutional_error_handler),
    )
    app.add_exception_handler(MACIErrorType, cast(_Handler, maci_error_handler))
    app.add_exception_handler(PolicyErrorType, cast(_Handler, policy_error_handler))
    app.add_exception_handler(AgentErrorType, cast(_Handler, agent_error_handler))
    app.add_exception_handler(MessageErrorType, cast(_Handler, message_error_handler))
    app.add_exception_handler(
        BusOperationErrorType,
        cast(_Handler, bus_operation_error_handler),
    )
    app.add_exception_handler(AgentBusErrorType, cast(_Handler, agent_bus_error_handler))
    app.add_exception_handler(Exception, cast(_Handler, global_exception_handler))

    logger.info("All exception handlers registered successfully")
