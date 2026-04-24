"""Regression coverage for split-package cleanup surfaces."""

from __future__ import annotations

from enhanced_agent_bus import message_processor as message_processor_module
from enhanced_agent_bus.message_processor import (
    governance_bridge,
    metering_bridge,
    validator,
)
from enhanced_agent_bus.message_processor import (
    router as message_router,
)
from enhanced_agent_bus.routes import tenants as tenants_module
from enhanced_agent_bus.routes.tenants import _shared as tenant_shared
from enhanced_agent_bus.routes.tenants import crud, hierarchy, lifecycle, quota


def test_message_processor_split_surfaces_reexport_canonical_processor() -> None:
    assert message_router.MessageProcessor is message_processor_module.MessageProcessor
    assert metering_bridge.MessageProcessor is message_processor_module.MessageProcessor
    assert governance_bridge.MessageProcessor is message_processor_module.MessageProcessor
    assert validator.MessageProcessor is message_processor_module.MessageProcessor


def test_tenant_section_surfaces_reexport_canonical_router() -> None:
    assert crud.router is tenants_module.router
    assert lifecycle.router is tenants_module.router
    assert quota.router is tenants_module.router
    assert hierarchy.router is tenants_module.router


def test_tenant_shared_exports_only_public_names() -> None:
    assert tenant_shared.__all__ == [
        "get_admin_tenant_id",
        "get_manager",
        "get_optional_tenant_id",
    ]
    assert not any(name.startswith("_") for name in tenant_shared.__all__)


def test_tenant_shared_private_helpers_remain_explicit_attributes() -> None:
    assert tenant_shared._authenticate_via_api_key is tenants_module._authenticate_via_api_key
    assert tenant_shared._authenticate_via_jwt is tenants_module._authenticate_via_jwt
    assert tenant_shared._build_tenant_list_response is tenants_module._build_tenant_list_response
    assert tenant_shared._configured_jwt_algorithm is tenants_module._configured_jwt_algorithm
    assert tenant_shared._get_tenant_or_404 is tenants_module._get_tenant_or_404
    assert tenant_shared._tenant_response is tenants_module._tenant_response
