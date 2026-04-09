"""
ACGS-2 Enhanced Agent Bus Middleware
Constitutional Hash: 608508a9bd224290

This module provides middleware configuration for the API,
including CORS, security headers, tenant context, and API versioning.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Awaitable, Callable
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from enhanced_agent_bus.observability.structured_logging import get_logger

_CorrelationMiddleware = Callable[
    [Request, Callable[[Request], Awaitable[Response]]],
    Awaitable[Response],
]
_CorrelationMiddlewareFactory = Callable[[], _CorrelationMiddleware]

# Initialize logging
logger: Any
create_correlation_middleware: _CorrelationMiddlewareFactory | None
try:
    from enhanced_agent_bus._compat.acgs_logging import (
        create_correlation_middleware as _create_correlation_middleware,
    )
    from enhanced_agent_bus._compat.acgs_logging import (
        init_service_logging,
    )

    create_correlation_middleware = _create_correlation_middleware
    logger = init_service_logging("enhanced-agent-bus", level="INFO", json_format=True)
except ImportError:
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)
    logger = get_logger(__name__)
    create_correlation_middleware = None

# Security imports
SecurityHeadersConfig: type[Any]
SecurityHeadersMiddleware: type[Any]
TenantContextConfig: type[Any]
TenantContextMiddleware: type[Any]
get_cors_config: Callable[..., dict[str, object]]
try:
    from src.core.shared.security.cors_config import get_cors_config as _get_cors_config
    _security_headers = importlib.import_module("src.core.shared.security.security_headers")
    _tenant_context = importlib.import_module("src.core.shared.security.tenant_context")

    get_cors_config = cast(Callable[..., dict[str, object]], _get_cors_config)
    SecurityHeadersConfig = cast(type[Any], _security_headers.SecurityHeadersConfig)
    SecurityHeadersMiddleware = cast(
        type[Any], _security_headers.SecurityHeadersMiddleware
    )
    TenantContextConfig = cast(type[Any], _tenant_context.TenantContextConfig)
    TenantContextMiddleware = cast(
        type[Any], _tenant_context.TenantContextMiddleware
    )
    SECURITY_HEADERS_AVAILABLE = True
except ImportError:
    SECURITY_HEADERS_AVAILABLE = False
    _fallback_stubs = importlib.import_module("enhanced_agent_bus.fallback_stubs")

    get_cors_config = cast(
        Callable[..., dict[str, object]], _fallback_stubs.stub_get_cors_config
    )
    SecurityHeadersConfig = cast(type[Any], _fallback_stubs.StubSecurityHeadersConfig)
    SecurityHeadersMiddleware = cast(
        type[Any], _fallback_stubs.StubSecurityHeadersMiddleware
    )
    TenantContextConfig = cast(type[Any], _fallback_stubs.StubTenantContextConfig)
    TenantContextMiddleware = cast(
        type[Any], _fallback_stubs.StubTenantContextMiddleware
    )

# API Versioning Middleware
API_VERSIONING_AVAILABLE = False
APIVersioningMiddleware: Any | None = None
VersioningConfig: Any | None = None
try:
    from src.core.shared.api_versioning import (
        APIVersioningMiddleware as _APIVersioningMiddleware,
    )
    from src.core.shared.api_versioning import (
        VersioningConfig as _VersioningConfig,
    )

    APIVersioningMiddleware = _APIVersioningMiddleware
    VersioningConfig = _VersioningConfig
    API_VERSIONING_AVAILABLE = True
except ImportError:
    pass

# Correlation ID middleware from api_exceptions
from ..api_exceptions import (
    correlation_id_middleware,
)


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware for the application."""
    app.add_middleware(CORSMiddleware, **cast(Any, get_cors_config()))


def setup_tenant_context_middleware(app: FastAPI) -> None:
    """Configure tenant context middleware for the application."""
    tenant_config = TenantContextConfig.from_env()
    if os.environ.get("ENVIRONMENT") == "development":
        tenant_config.required = False
    app.add_middleware(cast(Any, TenantContextMiddleware), config=tenant_config)
    logger.info(
        "Tenant context middleware enabled",
        extra={
            "required": tenant_config.required,
            "exempt_paths": tenant_config.exempt_paths,
        },
    )


def setup_security_headers_middleware(app: FastAPI) -> None:
    """Configure security headers middleware for the application."""
    if not SECURITY_HEADERS_AVAILABLE:
        logger.warning("Security headers middleware not available - missing import")
        return

    environment = os.environ.get("ENVIRONMENT", "production").lower()
    security_config = (
        SecurityHeadersConfig.for_development()
        if environment == "development"
        else SecurityHeadersConfig.for_production()
    )
    app.add_middleware(cast(Any, SecurityHeadersMiddleware), config=security_config)
    logger.info(
        "Security headers middleware enabled",
        extra={"environment": environment},
    )


def setup_api_versioning_middleware(app: FastAPI) -> None:
    """Configure API versioning middleware for the application."""
    if not API_VERSIONING_AVAILABLE or APIVersioningMiddleware is None or VersioningConfig is None:
        logger.warning("API versioning middleware not available - missing import")
        return

    versioning_config = VersioningConfig(
        default_version="v1",
        supported_versions=("v1", "v2"),
        deprecated_versions=(),
        exempt_paths={
            "/health",
            "/health/live",
            "/health/ready",
            "/ready",
            "/live",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        },
        enable_metrics=True,
        strict_versioning=False,
        log_version_usage=True,
    )
    app.add_middleware(cast(Any, APIVersioningMiddleware), config=versioning_config)
    logger.info(
        "API versioning middleware enabled",
        extra={
            "default_version": versioning_config.default_version,
            "supported_versions": list(versioning_config.supported_versions),
        },
    )


def setup_correlation_id_middleware(app: FastAPI) -> None:
    """Configure correlation ID middleware for the application."""
    if create_correlation_middleware is None:
        return
    correlation_mw = create_correlation_middleware()
    if correlation_mw is None:
        return
    app.middleware("http")(correlation_mw)


def setup_all_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    setup_correlation_id_middleware(app)
    setup_cors_middleware(app)
    setup_tenant_context_middleware(app)
    setup_security_headers_middleware(app)
    setup_api_versioning_middleware(app)


__all__ = [
    "API_VERSIONING_AVAILABLE",
    "SECURITY_HEADERS_AVAILABLE",
    "correlation_id_middleware",
    "logger",
    "setup_all_middleware",
    "setup_api_versioning_middleware",
    "setup_correlation_id_middleware",
    "setup_cors_middleware",
    "setup_security_headers_middleware",
    "setup_tenant_context_middleware",
]
