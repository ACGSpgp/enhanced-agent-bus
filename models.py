"""
ACGS-2 Enhanced Agent Bus - Models
Constitutional Hash: 608508a9bd224290

Data models for agent communication and message handling.

NOTE: This file has been refactored. Models are now organized into:
- enums.py: All enumeration types
- agent_models.py: SwarmAgent and agent-related models
- batch_models.py: Batch processing models
- session_models.py: Session governance models
- core_models.py: Core message and routing models

This file re-exports all models for backward compatibility.
New code should import directly from the specific modules.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, TypeAlias

# Ensure module aliasing across package import paths
_module = sys.modules.get(__name__)
if _module is not None:
    sys.modules.setdefault("enhanced_agent_bus.models", _module)
    sys.modules.setdefault("core.enhanced_agent_bus.models", _module)

# Import constitutional hash
try:
    from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "standalone"

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import (
        JSONDict,
        JSONValue,
        MetadataDict,
        PerformanceMetrics,
        SecurityContext,
    )
else:
    try:
        from enhanced_agent_bus._compat.types import (
            JSONDict,
            JSONValue,
            MetadataDict,
            PerformanceMetrics,
            SecurityContext,
        )
    except ImportError:
        # Fallback for standalone usage
        JSONValue: TypeAlias = object
        JSONDict: TypeAlias = dict[str, object]
        SecurityContext: TypeAlias = JSONDict
        MetadataDict: TypeAlias = JSONDict
        PerformanceMetrics: TypeAlias = dict[str, int | float | str | None]

if TYPE_CHECKING:
    from .constitutional.version_model import (
        ConstitutionalStatus,
        ConstitutionalVersion,
    )
else:
    try:
        from .constitutional.version_model import (
            ConstitutionalStatus,
            ConstitutionalVersion,
        )
    except ImportError:
        ConstitutionalVersion: Any = None
        ConstitutionalStatus: Any = None

# Re-export enums
# Re-export agent models
try:
    from .agent_models import SwarmAgent
except ImportError:
    from enhanced_agent_bus.agent_models import SwarmAgent

# Re-export batch models
try:
    from .batch_models import (
        BatchRequest,
        BatchRequestItem,
        BatchResponse,
        BatchResponseItem,
        BatchResponseStats,
    )
except ImportError:
    from enhanced_agent_bus.batch_models import (
        BatchRequest,
        BatchRequestItem,
        BatchResponse,
        BatchResponseItem,
        BatchResponseStats,
    )

# Re-export core models
from .core_models import (
    AgentMessage,
    ConversationMessage,
    ConversationState,
    DecisionLog,
    EnumOrString,
    MessageContent,
    PQCMetadata,
    RoutingContext,
    get_enum_value,
)
from .enums import (
    AgentCapability,
    AutonomyTier,
    BatchItemStatus,
    MessageStatus,
    MessageType,
    Priority,
    RiskLevel,
    TaskComplexity,
    TaskType,
    ValidationStatus,
)

# Re-export schema evolution (T012: Event Schema Evolution)
from .schema_evolution import (
    AGENT_MESSAGE_SCHEMA_V1,
    AGENT_MESSAGE_SCHEMA_V1_1,
    AGENT_MESSAGE_SCHEMA_V1_2,
    CompatibilityChecker,
    EvolutionType,
    MigrationStatus,
    SchemaCompatibility,
    SchemaDefinition,
    SchemaEvolutionChange,
    SchemaFieldDefinition,
    SchemaMigration,
    SchemaMigrator,
    SchemaRegistry,
    SchemaVersion,
    VersionedMessageBase,
    create_default_registry,
)

# Re-export session models
from .session_models import (
    SessionContext,
    SessionGovernanceConfig,
)

# Re-export LangGraph orchestration models for backward compatibility
try:
    from .langgraph_orchestration.models import (
        Checkpoint,
        CheckpointStatus,
        ConditionalEdge,
        ExecutionContext,
        ExecutionResult,
        ExecutionStatus,
        GraphConfig,
        GraphDefinition,
        GraphEdge,
        GraphNode,
        GraphState,
        InterruptRequest,
        InterruptResponse,
        InterruptType,
        NodeResult,
        NodeStatus,
        NodeType,
    )
except ImportError:
    pass

# Constants for message constraints
MAX_PAYLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10MB default cap

__all__ = [
    "AGENT_MESSAGE_SCHEMA_V1",
    "AGENT_MESSAGE_SCHEMA_V1_1",
    "AGENT_MESSAGE_SCHEMA_V1_2",
    # Constants
    "CONSTITUTIONAL_HASH",
    "MAX_PAYLOAD_SIZE_BYTES",
    "AgentCapability",
    "AgentMessage",
    "AutonomyTier",
    "BatchItemStatus",
    # Batch processing models
    "BatchRequest",
    "BatchRequestItem",
    "BatchResponse",
    "BatchResponseItem",
    "BatchResponseStats",
    # LangGraph orchestration models
    "Checkpoint",
    "CompatibilityChecker",
    "ConditionalEdge",
    "ConstitutionalStatus",
    # Constitutional models
    "ConstitutionalVersion",
    # Pydantic models for multi-turn conversation support
    "ConversationMessage",
    "ConversationState",
    "DecisionLog",
    "EnumOrString",
    "EvolutionType",
    "ExecutionContext",
    # type aliases
    "MessageContent",
    "MessageStatus",
    # Enums
    "MessageType",
    "MetadataDict",
    "MigrationStatus",
    "PQCMetadata",
    "PerformanceMetrics",
    "Priority",
    "RiskLevel",
    # Data classes
    "RoutingContext",
    "SchemaCompatibility",
    "SchemaDefinition",
    "SchemaEvolutionChange",
    "SchemaFieldDefinition",
    "SchemaMigration",
    "SchemaMigrator",
    "SchemaRegistry",
    # Schema Evolution (T012)
    "SchemaVersion",
    "SecurityContext",
    "SessionContext",
    # Session governance models
    "SessionGovernanceConfig",
    "SwarmAgent",
    "TaskComplexity",
    "TaskType",
    "ValidationStatus",
    "VersionedMessageBase",
    "create_default_registry",
    # Utility functions
    "get_enum_value",
    # LangGraph orchestration models
    "Checkpoint",
    "CheckpointStatus",
    "ConditionalEdge",
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionStatus",
    "GraphConfig",
    "GraphDefinition",
    "GraphEdge",
    "GraphNode",
    "GraphState",
    "InterruptRequest",
    "InterruptResponse",
    "InterruptType",
    "NodeResult",
    "NodeStatus",
    "NodeType",
]
