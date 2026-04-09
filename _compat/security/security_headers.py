"""Shim for src.core.shared.security.security_headers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.security.security_headers import (  # noqa: F401
        SecurityHeadersConfig,
        SecurityHeadersMiddleware,
        add_security_headers,
    )
else:
    try:
        from src.core.shared.security import security_headers as _shared_security_headers
    except ImportError:
        _shared_security_headers = None

    if _shared_security_headers is not None:
        SecurityHeadersConfig = _shared_security_headers.SecurityHeadersConfig
        SecurityHeadersMiddleware = _shared_security_headers.SecurityHeadersMiddleware
        add_security_headers = _shared_security_headers.add_security_headers
    else:

        @dataclass
        class SecurityHeadersConfig:
            csp_enabled: bool = True
            hsts_enabled: bool = True
            frame_options: str = "DENY"
            content_type_options: str = "nosniff"
            xss_protection: str = "1; mode=block"
            extra_headers: dict[str, str] = field(default_factory=dict)

            @classmethod
            def for_development(cls) -> "SecurityHeadersConfig":
                return cls(csp_enabled=False, hsts_enabled=False, frame_options="SAMEORIGIN")

            @classmethod
            def for_production(cls) -> "SecurityHeadersConfig":
                return cls()

        class SecurityHeadersMiddleware:
            """No-op security headers middleware stub."""

            def __init__(self, app: Any = None, **kwargs: Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
                if self.app is not None:
                    await self.app(scope, receive, send)

        def add_security_headers(app: Any) -> None:
            del app

    __all__ = [
        "SecurityHeadersConfig",
        "SecurityHeadersMiddleware",
        "add_security_headers",
    ]
