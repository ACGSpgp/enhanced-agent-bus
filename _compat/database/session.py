"""Shim for src.core.shared.database.session."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.database.session import *  # noqa: F403
else:
    try:
        from src.core.shared.database.session import *  # noqa: F403
    except ImportError:
        try:
            from sqlalchemy.orm import declarative_base
        except ImportError:
            Base: Any = None
        else:
            Base = declarative_base()

        engine: Any = None
        SessionLocal: Any = None

        async def get_db() -> Any:
            """Stub: yields None (no real DB in standalone mode)."""
            yield None

        async def init_db() -> None:
            """No-op database initialization."""
