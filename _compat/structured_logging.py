"""Shim for src.core.shared.structured_logging."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.shared.structured_logging import *  # noqa: F403
    from src.core.shared.structured_logging import (
        configure_logging,
        get_correlation_id,
        get_logger,
        get_tenant_id,
        set_correlation_id,
        set_tenant_id,
    )
else:
    try:
        from src.core.shared.structured_logging import *  # noqa: F403
        from src.core.shared.structured_logging import (
            configure_logging,
            get_correlation_id,
            get_logger,
            get_tenant_id,
            set_correlation_id,
            set_tenant_id,
        )
    except ImportError:

        class _KwargsLogger(logging.LoggerAdapter[logging.Logger]):
            """Logger that accepts and discards extra kwargs (detail=, etc.)."""

            def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
                # Strip non-stdlib kwargs
                clean = {
                    k: v
                    for k, v in kwargs.items()
                    if k in ("exc_info", "stack_info", "stacklevel", "extra")
                }
                return msg, clean

        def get_logger(name: str) -> _KwargsLogger:
            """Return a kwargs-tolerant logger as a structlog stand-in."""
            base = logging.getLogger(name)
            if not base.handlers and not base.parent:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
                )
                base.addHandler(handler)
            return _KwargsLogger(base, {})

        def configure_logging(
            level: str | None = None,
            format_type: str | None = None,
            include_stack_trace: bool = True,
            redact_sensitive: bool = True,
        ) -> None:
            del level, format_type, include_stack_trace, redact_sensitive

        def set_correlation_id(correlation_id: str | None = None) -> str:
            return correlation_id or "standalone"

        def get_correlation_id() -> str:
            return "standalone"

        def set_tenant_id(tenant_id: str) -> None:
            del tenant_id

        def get_tenant_id() -> str:
            return "default"

        def log_function_call(logger: Any = None) -> Any:
            """No-op decorator."""

            def decorator(func: Any) -> Any:
                return func

            return decorator
