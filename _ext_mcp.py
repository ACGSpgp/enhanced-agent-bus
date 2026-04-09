# Constitutional Hash: 608508a9bd224290
"""Optional MCP Native Integration Module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .mcp_integration import (
        MCP_CLIENT_AVAILABLE,
        MCP_SERVER_AVAILABLE,
        MCP_TOOL_REGISTRY_AVAILABLE,
        MCP_VALIDATORS_AVAILABLE,
        MCPClient,
        MCPClientConfig,
        MCPClientState,
        MCPConnectionError,
        MCPConnectionPool,
        MCPConstitutionalValidator,
        MCPIntegrationConfig,
        MCPIntegrationServer,
        MCPOperationContext,
        MCPServerConnection,
        MCPServerMetrics,
        MCPServerState,
        MCPToolRegistry,
        MCPValidationConfig,
        MCPValidationResult,
        OperationType,
        create_mcp_client,
        create_mcp_integration_server,
        create_mcp_validator,
        create_tool_registry,
    )
else:
    try:
        from .mcp_integration import (
            MCP_CLIENT_AVAILABLE,
            MCP_SERVER_AVAILABLE,
            MCP_TOOL_REGISTRY_AVAILABLE,
            MCP_VALIDATORS_AVAILABLE,
            MCPClient,
            MCPClientConfig,
            MCPClientState,
            MCPConnectionError,
            MCPConnectionPool,
            MCPConstitutionalValidator,
            MCPIntegrationConfig,
            MCPIntegrationServer,
            MCPOperationContext,
            MCPServerConnection,
            MCPServerMetrics,
            MCPServerState,
            MCPToolRegistry,
            MCPValidationConfig,
            MCPValidationResult,
            OperationType,
            create_mcp_client,
            create_mcp_integration_server,
            create_mcp_validator,
            create_tool_registry,
        )

        MCP_INTEGRATION_AVAILABLE = True
    except ImportError:
        MCP_INTEGRATION_AVAILABLE = False
        MCP_CLIENT_AVAILABLE = False
        MCP_SERVER_AVAILABLE = False
        MCP_TOOL_REGISTRY_AVAILABLE = False
        MCP_VALIDATORS_AVAILABLE = False
        MCPClient: Any = object
        MCPClientConfig: Any = object
        MCPClientState: Any = object
        MCPConnectionError: Any = object
        MCPConnectionPool: Any = object
        MCPConstitutionalValidator: Any = object
        MCPIntegrationConfig: Any = object
        MCPIntegrationServer: Any = object
        MCPOperationContext: Any = object
        MCPServerConnection: Any = object
        MCPServerMetrics: Any = object
        MCPServerState: Any = object
        MCPToolRegistry: Any = object
        MCPValidationConfig: Any = object
        MCPValidationResult: Any = object
        OperationType: Any = object
        create_mcp_client: Any = object
        create_mcp_integration_server: Any = object
        create_mcp_validator: Any = object
        create_tool_registry: Any = object

_EXT_ALL = [
    "MCP_INTEGRATION_AVAILABLE",
    "MCP_CLIENT_AVAILABLE",
    "MCP_SERVER_AVAILABLE",
    "MCP_TOOL_REGISTRY_AVAILABLE",
    "MCP_VALIDATORS_AVAILABLE",
    "MCPClient",
    "MCPClientConfig",
    "MCPClientState",
    "MCPConnectionError",
    "MCPConnectionPool",
    "MCPConstitutionalValidator",
    "MCPIntegrationConfig",
    "MCPIntegrationServer",
    "MCPOperationContext",
    "MCPServerConnection",
    "MCPServerMetrics",
    "MCPServerState",
    "MCPToolRegistry",
    "MCPValidationConfig",
    "MCPValidationResult",
    "OperationType",
    "create_mcp_client",
    "create_mcp_integration_server",
    "create_mcp_validator",
    "create_tool_registry",
]
