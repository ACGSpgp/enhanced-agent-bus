"""Shared dependencies and helpers for tenant route submodules.

Structural surface for future refactor. The implementation currently lives in
``routes/tenants/__init__.py`` (original 1,443-line router preserved intact
to guarantee HTTP contract stability). This module re-exports the symbols that
the per-section sub-routers (crud, lifecycle, quota, hierarchy) would consume
once the endpoint extraction is performed.
"""

from __future__ import annotations

from . import (
    _authenticate_via_api_key,
    _authenticate_via_jwt,
    _build_tenant_list_response,
    _configured_jwt_algorithm,
    _get_tenant_or_404,
    _tenant_response,
    get_admin_tenant_id,
    get_manager,
    get_optional_tenant_id,
)

__all__ = [
    "_authenticate_via_api_key",
    "_authenticate_via_jwt",
    "_build_tenant_list_response",
    "_configured_jwt_algorithm",
    "_get_tenant_or_404",
    "_tenant_response",
    "get_admin_tenant_id",
    "get_manager",
    "get_optional_tenant_id",
]
