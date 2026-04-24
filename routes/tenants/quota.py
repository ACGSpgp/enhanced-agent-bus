"""Quota management section of the tenant management API.

Structural surface — the endpoints currently live in
``routes/tenants/__init__.py`` (lines 1141-1351 in the pre-split file). This
module documents the logical grouping and re-exports the router for a future
extraction where these endpoints will move here verbatim.

Section endpoints (all under prefix ``/api/v1/tenants``):
    PUT    /{tenant_id}/quota             update_tenant_quota
    POST   /{tenant_id}/quota/check       check_quota
    GET    /{tenant_id}/usage             get_tenant_usage
    POST   /{tenant_id}/usage/increment   increment_usage
"""

from __future__ import annotations

from . import router

__all__ = ["router"]
