"""
Danger-signal analysis for adaptive governance quorum decisions.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict
else:
    JSONDict: TypeAlias = dict[str, object]


class DangerSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AdaptiveQuorumMode(str, Enum):
    MAJORITY = "majority"
    SUPER_MAJORITY = "super_majority"
    UNANIMOUS = "unanimous"


@dataclass(frozen=True, slots=True)
class DangerSignal:
    signal_id: str
    severity: DangerSeverity
    score: float
    reason: str
    metadata: JSONDict = field(default_factory=dict)

    def to_metadata(self) -> JSONDict:
        return {
            "signal_id": self.signal_id,
            "severity": self.severity.value,
            "score": self.score,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AdaptiveQuorumDecision:
    mode: AdaptiveQuorumMode
    risk_score: float
    required_votes: int
    total_validators: int
    signals: tuple[DangerSignal, ...] = ()

    def to_metadata(self) -> JSONDict:
        return {
            "mode": self.mode.value,
            "risk_score": self.risk_score,
            "required_votes": self.required_votes,
            "total_validators": self.total_validators,
            "signals": [signal.to_metadata() for signal in self.signals],
        }


class DangerSignalAnalyzer:
    """Compute risk signals and derive an adaptive quorum requirement."""

    _CLINICAL_KEYWORDS = (
        "patient",
        "phi",
        "mrn",
        "diagnosis",
        "insurance",
        "clinical",
        "fhir",
        "dob",
    )
    _DESTRUCTIVE_KEYWORDS = (
        "override",
        "disable",
        "bypass",
        "delete",
        "revoke",
        "transfer",
        "payment",
    )

    def analyze(
        self,
        *,
        content: str,
        action_type: str,
        impact_score: float | None,
        requires_independent_validator: bool,
        security_scan_result: str | None,
        validator_count: int,
    ) -> AdaptiveQuorumDecision:
        normalized = content.lower()
        signals: list[DangerSignal] = []

        if impact_score is not None and impact_score >= 0.85:
            signals.append(
                DangerSignal(
                    signal_id="high_impact_score",
                    severity=DangerSeverity.HIGH
                    if impact_score < 0.95
                    else DangerSeverity.CRITICAL,
                    score=min(1.0, impact_score),
                    reason="Impact score indicates elevated governance risk.",
                    metadata={"impact_score": impact_score},
                )
            )

        if any(keyword in normalized for keyword in self._CLINICAL_KEYWORDS):
            signals.append(
                DangerSignal(
                    signal_id="clinical_data_path",
                    severity=DangerSeverity.HIGH,
                    score=0.8,
                    reason="Clinical/PHI-adjacent content detected.",
                )
            )

        if any(keyword in normalized for keyword in self._DESTRUCTIVE_KEYWORDS):
            signals.append(
                DangerSignal(
                    signal_id="destructive_or_privileged_action",
                    severity=DangerSeverity.CRITICAL,
                    score=0.95,
                    reason="Destructive or privileged action keywords detected.",
                )
            )

        if action_type in {"governance_request", "constitutional_validation"}:
            signals.append(
                DangerSignal(
                    signal_id="governance_control_plane",
                    severity=DangerSeverity.MEDIUM,
                    score=0.65,
                    reason="Control-plane governance action requires stronger review.",
                    metadata={"action_type": action_type},
                )
            )

        if requires_independent_validator:
            signals.append(
                DangerSignal(
                    signal_id="independent_validator_required",
                    severity=DangerSeverity.MEDIUM,
                    score=0.7,
                    reason="Independent validator gate already classified this action as high-impact.",
                )
            )

        if security_scan_result and security_scan_result.lower() != "passed":
            signals.append(
                DangerSignal(
                    signal_id="security_scan_not_clean",
                    severity=DangerSeverity.CRITICAL,
                    score=1.0,
                    reason="Security scan indicates unresolved risk.",
                    metadata={"security_scan_result": security_scan_result},
                )
            )

        risk_score = max(
            (signal.score for signal in signals), default=max(impact_score or 0.0, 0.0)
        )
        total_validators = max(0, validator_count)
        if total_validators <= 1:
            return AdaptiveQuorumDecision(
                mode=AdaptiveQuorumMode.UNANIMOUS,
                risk_score=risk_score,
                required_votes=total_validators,
                total_validators=total_validators,
                signals=tuple(signals),
            )

        if risk_score >= 0.85:
            mode = AdaptiveQuorumMode.UNANIMOUS
            required_votes = total_validators
        elif risk_score >= 0.55:
            mode = AdaptiveQuorumMode.SUPER_MAJORITY
            required_votes = math.ceil(total_validators * (2.0 / 3.0))
        else:
            mode = AdaptiveQuorumMode.MAJORITY
            required_votes = total_validators // 2 + 1

        return AdaptiveQuorumDecision(
            mode=mode,
            risk_score=risk_score,
            required_votes=required_votes,
            total_validators=total_validators,
            signals=tuple(signals),
        )


__all__ = [
    "AdaptiveQuorumDecision",
    "AdaptiveQuorumMode",
    "DangerSeverity",
    "DangerSignal",
    "DangerSignalAnalyzer",
]
