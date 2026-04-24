"""Lifecycle management section of the tenant management API.

Structural surface — the endpoints currently live in
``routes/tenants/__init__.py`` (lines 999-1139 in the pre-split file). This
module documents the logical grouping and re-exports the router for a future
extraction where these endpoints will move here verbatim.

Section endpoints (all under prefix ``/api/v1/tenants``):
    POST   /{tenant_id}/activate          activate_tenant
    POST   /{tenant_id}/deactivate        deactivate_tenant
    POST   /{tenant_id}/suspend           suspend_tenant
"""

from __future__ import annotations

from . import router

__all__ = ["router"]
