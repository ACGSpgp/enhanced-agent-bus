"""
ACGS-2 Enhanced Agent Bus API Routes
Constitutional Hash: 608508a9bd224290

This package contains all API route handlers organized by functionality.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_ROUTER_MODULES = {
    "batch_router": ".batch",
    "governance_router": ".governance",
    "health_router": ".health",
    "messages_router": ".messages",
    "policies_router": ".policies",
    "pqc_admin_router": ".pqc_admin",
    "workflows_router": ".workflows",
}


def __getattr__(name: str) -> Any:
    if name not in _ROUTER_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(_ROUTER_MODULES[name], __name__)
    router = module.router
    globals()[name] = router
    return router


__all__ = [
    "batch_router",
    "governance_router",
    "health_router",
    "messages_router",
    "policies_router",
    "pqc_admin_router",
    "workflows_router",
]
