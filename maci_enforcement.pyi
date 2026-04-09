"""
Typed stub for maci_enforcement.py
Constitutional Hash: cdd01ef066bc6cf2

Covers all symbols exported via __all__ to enable mypy checking
without requiring optional C-extensions to be installed.
"""

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Exceptions (re-exported from maci_errors for consistent class identity)
# ---------------------------------------------------------------------------

class MACIError(Exception): ...

class MACIRoleNotAssignedError(MACIError):
    agent_id: str
    action: str
    def __init__(self, agent_id: str, action: str) -> None: ...

class MACIRoleViolationError(MACIError):
    agent_id: str
    role: str
    action: str
    def __init__(self, agent_id: str, role: str, action: str) -> None: ...

class MACISelfValidationError(MACIError):
    agent_id: str
    action: str
    def __init__(self, agent_id: str, action: str) -> None: ...

class MACICrossRoleValidationError(MACIError):
    validator_id: str
    target_id: str
    def __init__(self, validator_id: str, target_id: str, reason: str = ...) -> None: ...

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MACIRole(str, Enum):
    PROPOSER = "proposer"
    SOLVER = "solver"
    VALIDATOR = "validator"
    OBSERVER = "observer"

class MACIAction(str, Enum):
    PROPOSE = "propose"
    SOLVE = "solve"
    VALIDATE = "validate"
    OBSERVE = "observe"
    EXECUTE = "execute"

# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

class MACIAgentRoleConfig:
    agent_id: str
    role: MACIRole
    capabilities: list[str]
    metadata: dict[str, Any]
    def __init__(
        self,
        agent_id: str,
        role: MACIRole,
        capabilities: list[str] = ...,
        metadata: dict[str, Any] = ...,
    ) -> None: ...

class MACIConfig:
    agents: list[MACIAgentRoleConfig]
    strict_mode: bool
    require_separation: bool
    def __init__(
        self,
        agents: list[MACIAgentRoleConfig] = ...,
        strict_mode: bool = ...,
        require_separation: bool = ...,
    ) -> None: ...

class MACIConfigLoader:
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MACIConfig: ...
    @classmethod
    def from_yaml(cls, path: str) -> MACIConfig: ...
    @classmethod
    def from_env(cls) -> MACIConfig: ...

# ---------------------------------------------------------------------------
# Registry and enforcement
# ---------------------------------------------------------------------------

class MACIAgentRecord:
    agent_id: str
    role: MACIRole
    outputs: list[str]
    registered_at: datetime
    metadata: dict[str, Any]
    constitutional_hash: str
    session_id: str | None
    def __init__(
        self,
        agent_id: str,
        role: MACIRole,
        outputs: list[str] = ...,
        registered_at: datetime = ...,
        metadata: dict[str, Any] = ...,
        constitutional_hash: str = ...,
        session_id: str | None = ...,
    ) -> None: ...

class MACIRoleRegistry:
    constitutional_hash: str
    async def register_agent(
        self,
        agent_id: str,
        role: MACIRole,
        metadata: dict[str, Any] | None = ...,
        session_id: str | None = ...,
    ) -> MACIAgentRecord: ...
    async def unregister_agent(
        self,
        agent_id: str,
        session_id: str | None = ...,
    ) -> MACIAgentRecord | None: ...
    async def get_agent(
        self,
        agent_id: str,
        session_id: str | None = ...,
    ) -> MACIAgentRecord | None: ...
    async def get_agents_by_role(
        self,
        role: MACIRole,
        session_id: str | None = ...,
    ) -> list[MACIAgentRecord]: ...
    async def get_session_agents(self, session_id: str) -> dict[str, MACIAgentRecord]: ...
    async def clear_session(self, session_id: str) -> int: ...
    async def record_output(
        self,
        agent_id: str,
        output_id: str,
        session_id: str | None = ...,
    ) -> None: ...
    async def get_output_producer(
        self,
        output_id: str,
        session_id: str | None = ...,
    ) -> str | None: ...
    async def is_self_output(
        self,
        agent_id: str,
        output_id: str,
        session_id: str | None = ...,
    ) -> bool: ...
    async def batch_record_outputs(
        self,
        agent_id: str,
        output_ids: list[str],
        session_id: str | None = ...,
    ) -> None: ...
    async def get_agent_role(self, agent_id: str) -> MACIRole | None: ...
    async def list_agents(self) -> list[MACIAgentRecord]: ...

class MACIEnforcer:
    registry: MACIRoleRegistry
    strict_mode: bool
    enable_session_audit: bool
    constitutional_hash: str
    def __init__(
        self,
        registry: MACIRoleRegistry | None = ...,
        config: MACIConfig | None = ...,
        strict_mode: bool = ...,
        enable_session_audit: bool = ...,
        role_matrix_validator: Any | None = ...,
    ) -> None: ...
    async def validate_action(
        self,
        agent_id: str,
        action: MACIAction,
        target_output_id: str | None = ...,
        target_agent_id: str | None = ...,
        session_id: str | None = ...,
    ) -> MACIValidationResult: ...
    async def check_permission(self, agent_id: str, action: MACIAction) -> bool: ...
    async def validate_cross_role(
        self,
        validator_id: str,
        target_id: str,
        action: MACIAction,
    ) -> bool: ...

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class MACIValidationResult:
    allowed: bool
    reason: str
    violations: list[str]
    confidence: float

class MACIValidationStrategy:
    async def validate(
        self,
        agent_id: str,
        action: MACIAction,
        context: dict[str, Any] | None = ...,
    ) -> MACIValidationResult: ...

class MACIValidationContext:
    agent_id: str
    action: MACIAction
    target_id: str | None
    metadata: dict[str, Any]

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[MACIRole, set[MACIAction]]
VALIDATION_CONSTRAINTS: dict[MACIRole, set[MACIRole]]

# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

def validate_maci_role_matrix(
    role_permissions: dict[MACIRole, set[MACIAction]] | None = ...,
    validation_constraints: dict[MACIRole, set[MACIRole]] | None = ...,
) -> list[str]: ...
async def apply_maci_config(registry: MACIRoleRegistry, config: MACIConfig) -> int: ...
def create_maci_enforcement_middleware(
    enforcer: MACIEnforcer | None = ...,
    extract_session: bool = ...,
) -> Callable[..., Any]: ...
