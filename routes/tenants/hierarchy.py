"""Hierarchy management section of the tenant management API.

Structural surface — the endpoints currently live in
``routes/tenants/__init__.py`` (lines 1353-end in the pre-split file). This
module documents the logical grouping and re-exports the router for a future
extraction where these endpoints will move here verbatim.

Section endpoints (all under prefix ``/api/v1/tenants``):
    GET    /{tenant_id}/hierarchy         get_tenant_hierarchy
    GET    /{tenant_id}/children          get_child_tenants
"""

from __future__ import annotations

from . import router

__all__ = ["router"]
