"""CRUD section of the tenant management API.

Structural surface — the endpoints currently live in
``routes/tenants/__init__.py`` (lines 720-997 in the pre-split file). This
module documents the logical grouping and re-exports the router for a future
extraction where these endpoints will move here verbatim.

Section endpoints (all under prefix ``/api/v1/tenants``):
    POST   /                              create_tenant
    GET    /                              list_tenants
    GET    /{tenant_id}                   get_tenant
    PATCH  /{tenant_id}                   update_tenant
    DELETE /{tenant_id}                   delete_tenant
    GET    /by-slug/{slug}                get_tenant_by_slug
"""

from __future__ import annotations

from . import router

__all__ = ["router"]
