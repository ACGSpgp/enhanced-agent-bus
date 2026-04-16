"""Canonical models for ACGS flywheel records.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

try:
    from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "standalone"

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict
else:
    try:
        from enhanced_agent_bus._compat.types import JSONDict
    except ImportError:
        JSONDict: TypeAlias = dict[str, Any]


class EvaluationMode(StrEnum):
    OFFLINE_REPLAY = "offline_replay"
    SHADOW = "shadow"
    CANARY = "canary"


class ApprovalState(StrEnum):
    """Lifecycle approval state for evidence bundles.

    Mirrors the canonical ``BundleStatus`` values defined in
    ``acgs_lite.constitution.bundle`` by convention (not import) so the
    two packages remain decoupled while sharing the same state vocabulary.
    """

    DRAFT = "draft"
    REVIEW = "review"
    EVAL = "eval"
    APPROVE = "approve"
    STAGED = "staged"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


VALID_APPROVAL_TRANSITIONS: dict[ApprovalState, set[ApprovalState]] = {
    ApprovalState.DRAFT: {ApprovalState.REVIEW, ApprovalState.WITHDRAWN},
    ApprovalState.REVIEW: {ApprovalState.EVAL, ApprovalState.REJECTED, ApprovalState.WITHDRAWN},
    ApprovalState.EVAL: {ApprovalState.APPROVE, ApprovalState.REJECTED, ApprovalState.WITHDRAWN},
    ApprovalState.APPROVE: {ApprovalState.STAGED, ApprovalState.REJECTED, ApprovalState.WITHDRAWN},
    ApprovalState.STAGED: {
        ApprovalState.ACTIVE,
        ApprovalState.ROLLED_BACK,
        ApprovalState.WITHDRAWN,
    },
    ApprovalState.ACTIVE: {ApprovalState.ROLLED_BACK, ApprovalState.SUPERSEDED},
    ApprovalState.ROLLED_BACK: {ApprovalState.DRAFT, ApprovalState.SUPERSEDED},
    ApprovalState.SUPERSEDED: set(),
    ApprovalState.REJECTED: set(),
    ApprovalState.WITHDRAWN: set(),
}


def validate_approval_transition(
    from_state: ApprovalState | str,
    to_state: ApprovalState | str,
) -> None:
    """Raise ``ValueError`` if *from_state* → *to_state* is not allowed."""
    src = ApprovalState(from_state)
    dst = ApprovalState(to_state)
    allowed = VALID_APPROVAL_TRANSITIONS.get(src, set())
    if dst not in allowed:
        raise ValueError(f"Invalid approval transition: {src.value!r} → {dst.value!r}")


class WorkloadKey(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=255)
    route_or_tool: str = Field(min_length=1, max_length=255)
    decision_kind: str = Field(min_length=1, max_length=255)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)

    @field_validator("tenant_id", "service", "route_or_tool", "decision_kind")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field must not be empty")
        return cleaned

    def as_key(self) -> str:
        return (
            f"{self.tenant_id}/{self.service}/{self.route_or_tool}/"
            f"{self.decision_kind}/{self.constitutional_hash}"
        )


class DecisionEvent(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    from_agent: str = Field(default="", max_length=255)
    validated_by_agent: str | None = Field(default=None, max_length=255)
    decision_kind: str = Field(min_length=1, max_length=100)
    request_context: JSONDict = Field(default_factory=dict)
    decision_payload: JSONDict = Field(default_factory=dict)
    latency_ms: float | None = None
    outcome: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeedbackEvent(BaseModel):
    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str | None = Field(default=None, max_length=255)
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    feedback_type: str = Field(min_length=1, max_length=100)
    outcome_status: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=5000)
    actual_impact: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: JSONDict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    record_count: int = Field(ge=0)
    redaction_status: str = Field(min_length=1, max_length=64)
    artifact_manifest_uri: str = Field(min_length=1)
    window_started_at: datetime | None = None
    window_ended_at: datetime | None = None
    source_counts: JSONDict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandidateArtifact(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    candidate_type: str = Field(min_length=1, max_length=100)
    candidate_spec: JSONDict = Field(default_factory=dict)
    parent_version: str | None = Field(default=None, max_length=255)
    status: str = Field(default="draft", min_length=1, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    candidate_id: str = Field(min_length=1, max_length=255)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    evaluation_mode: EvaluationMode
    status: str = Field(min_length=1, max_length=64)
    summary_metrics: JSONDict = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Legacy approval_state values that may exist in persisted records.
# Maps them to canonical ApprovalState values for backward compatibility.
_LEGACY_APPROVAL_STATE_MAP: dict[str, ApprovalState] = {
    "pending": ApprovalState.DRAFT,
    "pending_review": ApprovalState.REVIEW,
    "approved": ApprovalState.APPROVE,
    "published": ApprovalState.ACTIVE,
    "revoked": ApprovalState.WITHDRAWN,
}


class EvidenceBundle(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=255)
    workload_key: str = Field(min_length=1, max_length=512)
    candidate_id: str = Field(min_length=1, max_length=255)
    dataset_snapshot_id: str = Field(min_length=1, max_length=255)
    constitutional_hash: str = Field(default=CONSTITUTIONAL_HASH, min_length=1, max_length=64)
    approval_state: ApprovalState

    @field_validator("approval_state", mode="before")
    @classmethod
    def _coerce_legacy_approval_state(cls, value: object) -> object:
        """Accept legacy string values from persisted records."""
        if isinstance(value, ApprovalState):
            return value
        if isinstance(value, str):
            # Try canonical enum first
            try:
                return ApprovalState(value)
            except ValueError:
                pass
            # Fall back to legacy mapping
            mapped = _LEGACY_APPROVAL_STATE_MAP.get(value.lower().strip())
            if mapped is not None:
                return mapped
            # Unknown value — let Pydantic raise a clear error
        return value

    validator_records: list[JSONDict] = Field(default_factory=list)
    rollback_plan: JSONDict = Field(default_factory=dict)
    artifact_manifest_uri: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "ApprovalState",
    "CandidateArtifact",
    "DatasetSnapshot",
    "DecisionEvent",
    "EvaluationMode",
    "EvaluationRun",
    "EvidenceBundle",
    "FeedbackEvent",
    "VALID_APPROVAL_TRANSITIONS",
    "WorkloadKey",
    "validate_approval_transition",
]
