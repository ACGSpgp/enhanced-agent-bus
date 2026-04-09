"""Shim for src.core.shared.security.cors_config."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.security.cors_config import *  # noqa: F403
else:
    try:
        from src.core.shared.security.cors_config import *  # noqa: F403
    except ImportError:

        def get_cors_config(
            environment: object | None = None,
            additional_origins: list[str] | None = None,
            allow_credentials: bool = True,
        ) -> dict[str, Any]:
            """Return permissive CORS defaults for standalone / dev mode."""
            del environment, additional_origins, allow_credentials
            return {
                "allow_origins": ["*"],
                "allow_methods": ["*"],
                "allow_headers": ["*"],
                "allow_credentials": False,
            }

        def apply_cors(app: Any) -> None:
            """No-op CORS application stub."""
            del app
