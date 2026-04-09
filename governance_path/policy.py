"""Risk-tier policy rules for governance-path admission.

The policy layer maps message criticality to the minimum checkpoint set that
must appear in a governance path. The package intentionally fails closed:
ordering errors or missing checkpoints cause routing to be denied instead of
silently accepting a partially-governed path.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from .models import CheckpointType, GovernancePath


class RiskTier(StrEnum):
    """Risk levels that determine required governance checkpoints.

    Use these tiers to select progressively stricter path requirements. Higher
    tiers require more evidence that a message passed through MACI separation,
    impact scoring, and human oversight before delivery.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MACIPathPolicy:
    """Fail-closed checkpoint policy for MACI-style governance routing.

    This policy object validates a path against the minimum checkpoint set
    required for a specific risk tier. Use it wherever a router or gatekeeper
    needs a deterministic admission decision based on path evidence.

    Invariants:
        - Missing required checkpoints always reject the path.
        - Ordering validation happens before checkpoint presence checks.
        - Unknown checkpoint strings do not satisfy tier requirements.
    """

    REQUIRED_CHECKPOINTS: ClassVar[dict[RiskTier, set[CheckpointType]]] = {
        RiskTier.LOW: set(),
        RiskTier.MEDIUM: {CheckpointType.MACI_ROLE_CHECK},
        RiskTier.HIGH: {
            CheckpointType.MACI_ROLE_CHECK,
            CheckpointType.IMPACT_SCORING,
        },
        RiskTier.CRITICAL: {
            CheckpointType.MACI_ROLE_CHECK,
            CheckpointType.IMPACT_SCORING,
            CheckpointType.HUMAN_REVIEW,
        },
    }

    def validate_path(self, path: GovernancePath, risk_tier: RiskTier) -> tuple[bool, str | None]:
        """Validate ordering and required checkpoints for the requested risk tier.

        Args:
            path: Governance path to inspect.
            risk_tier: Risk tier that determines the minimum checkpoint set.

        Returns:
            A ``(is_valid, error)`` tuple. ``error`` is ``None`` when the path
            satisfies both ordering and required-checkpoint rules.
        """
        ordering_ok, ordering_error = path.validate_ordering()
        if not ordering_ok:
            return False, ordering_error

        present = {
            checkpoint
            for segment in path.segments
            for raw_check in segment.checks_performed
            for checkpoint in [CheckpointType.parse(raw_check)]
            if checkpoint is not None
        }
        missing = sorted(
            checkpoint.name for checkpoint in self.REQUIRED_CHECKPOINTS[risk_tier] - present
        )
        if missing:
            return False, f"Missing required checkpoints: {', '.join(missing)}"
        return True, None
