"""
ACGS-2 MCP Native Integration Module.

Provides comprehensive Model Context Protocol (MCP) integration for the
Enhanced Agent Bus, enabling bidirectional communication with external
AI systems while maintaining constitutional governance.

Key Features:
- Bidirectional MCP protocol support (client and server modes)
- Tool discovery and registration with constitutional validation
- MACI-aware role-based access control for MCP operations
- Support for 16,000+ MCP server compatibility
- Comprehensive audit logging and compliance tracking

Constitutional Hash: 608508a9bd224290

Usage:
    from enhanced_agent_bus.mcp_integration import (
        MCPClient,
        MCPIntegrationServer,
        MCPToolRegistry,
        MCPConstitutionalValidator,
    )

    # Create MCP client for connecting to external servers
    client = MCPClient(config=MCPClientConfig(server_url="http://localhost:8000"))
    await client.connect()

    # Create MCP server for exposing ACGS-2 capabilities
    server = MCPIntegrationServer(config=MCPIntegrationConfig())
    await server.start()
"""

import sys
from typing import TYPE_CHECKING, Any

__version__ = "1.0.0"

# Import centralized constitutional hash
try:
    from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "standalone"

__constitutional_hash__ = CONSTITUTIONAL_HASH
MCP_CLIENT_AVAILABLE = False
MCP_SERVER_AVAILABLE = False
MCP_TOOL_REGISTRY_AVAILABLE = False
MCP_VALIDATORS_AVAILABLE = False

_module = sys.modules.get(__name__)
if _module is not None:
    sys.modules.setdefault("enhanced_agent_bus.mcp_integration", _module)
    sys.modules.setdefault("packages.enhanced_agent_bus.mcp_integration", _module)

if TYPE_CHECKING:
    from .client import (
        MCPClient,
        MCPClientConfig,
        MCPClientState,
        MCPConnectionError,
        MCPConnectionPool,
        MCPServerConnection,
        create_mcp_client,
    )
    from .server import (
        MCPIntegrationConfig,
        MCPIntegrationServer,
        MCPServerMetrics,
        MCPServerState,
        create_mcp_integration_server,
    )
    from .tool_registry import (
        ExternalTool,
        MCPToolRegistry,
        ToolCapability,
        ToolDiscoveryResult,
        ToolExecutionContext,
        ToolRegistrationResult,
        create_tool_registry,
    )
    from .validators import (
        MCPConstitutionalValidator,
        MCPOperationContext,
        MCPValidationConfig,
        MCPValidationResult,
        OperationType,
        create_mcp_validator,
    )
else:
    # MCP Client
    try:
        from .client import (
            MCPClient,
            MCPClientConfig,
            MCPClientState,
            MCPConnectionError,
            MCPConnectionPool,
            MCPServerConnection,
            create_mcp_client,
        )

        MCP_CLIENT_AVAILABLE = True
    except ImportError:
        MCP_CLIENT_AVAILABLE = False
        MCPClient: Any = object
        MCPClientConfig: Any = object
        MCPClientState: Any = object
        MCPConnectionError: Any = object
        MCPConnectionPool: Any = object
        MCPServerConnection: Any = object
        create_mcp_client: Any = object

    # MCP Server
    try:
        from .server import (
            MCPIntegrationConfig,
            MCPIntegrationServer,
            MCPServerMetrics,
            MCPServerState,
            create_mcp_integration_server,
        )

        MCP_SERVER_AVAILABLE = True
    except ImportError:
        MCP_SERVER_AVAILABLE = False
        MCPIntegrationConfig: Any = object
        MCPIntegrationServer: Any = object
        MCPServerMetrics: Any = object
        MCPServerState: Any = object
        create_mcp_integration_server: Any = object

    # Tool Registry
    try:
        from .tool_registry import (
            ExternalTool,
            MCPToolRegistry,
            ToolCapability,
            ToolDiscoveryResult,
            ToolExecutionContext,
            ToolRegistrationResult,
            create_tool_registry,
        )

        MCP_TOOL_REGISTRY_AVAILABLE = True
    except ImportError:
        MCP_TOOL_REGISTRY_AVAILABLE = False
        ExternalTool: Any = object
        MCPToolRegistry: Any = object
        ToolCapability: Any = object
        ToolDiscoveryResult: Any = object
        ToolExecutionContext: Any = object
        ToolRegistrationResult: Any = object
        create_tool_registry: Any = object

    # Constitutional Validators
    try:
        from .validators import (
            MCPConstitutionalValidator,
            MCPOperationContext,
            MCPValidationConfig,
            MCPValidationResult,
            OperationType,
            create_mcp_validator,
        )

        MCP_VALIDATORS_AVAILABLE = True
    except ImportError:
        MCP_VALIDATORS_AVAILABLE = False
        MCPConstitutionalValidator: Any = object
        MCPOperationContext: Any = object
        MCPValidationConfig: Any = object
        MCPValidationResult: Any = object
        OperationType: Any = object
        create_mcp_validator: Any = object

__all__ = [
    "CONSTITUTIONAL_HASH",
    # Availability flags
    "MCP_CLIENT_AVAILABLE",
    "MCP_SERVER_AVAILABLE",
    "MCP_TOOL_REGISTRY_AVAILABLE",
    "MCP_VALIDATORS_AVAILABLE",
    # Tool Registry
    "ExternalTool",
    # Client
    "MCPClient",
    "MCPClientConfig",
    "MCPClientState",
    "MCPConnectionError",
    "MCPConnectionPool",
    # Validators
    "MCPConstitutionalValidator",
    # Server
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
    "ToolCapability",
    "ToolDiscoveryResult",
    "ToolExecutionContext",
    "ToolRegistrationResult",
    "__constitutional_hash__",
    # Module info
    "__version__",
    "create_mcp_client",
    "create_mcp_integration_server",
    "create_mcp_validator",
    "create_tool_registry",
]
