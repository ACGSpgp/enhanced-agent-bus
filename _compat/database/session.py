"""Shim for src.core.shared.database.session."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.database.session import *  # noqa: F403
else:
    try:
        from src.core.shared.database.session import *  # noqa: F403
    except ImportError:
        Base: Any = None
        engine: Any = None
        SessionLocal: Any = None

        async def get_db() -> Any:
            """Stub: yields None (no real DB in standalone mode)."""
            yield None

        async def init_db() -> None:
            """No-op database initialization."""
