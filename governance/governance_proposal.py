"""Governance proposal lifecycle: SuggestedRule → Polis → NMC → deployment."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acgs_lite.engine.synthesis import SuggestedRule


class ProposalStatus(StrEnum):
    PENDING = "pending"                     # Awaiting Polis vote
    DELIBERATING = "deliberating"           # Polis vote in progress
    CONSENSUS_REACHED = "consensus_reached" # NMC consensus done
    APPROVED = "approved"                   # Above threshold, ready to deploy
    REJECTED = "rejected"                   # Below threshold, dropped
    DEPLOYED = "deployed"                   # Rule live in constitution


@dataclass
class GovernanceProposal:
    proposal_id: str = field(default_factory=lambda: f"PROP-{uuid.uuid4().hex[:8].upper()}")
    suggested_rule: "SuggestedRule | None" = None
    rule_text: str = ""
    rule_id: str = ""
    rationale: str = ""
    confidence: float = 0.0
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    polis_statement_id: str | None = None
    polis_vote_count: int = 0
    polis_consensus_score: float = 0.0
    nmc_session_id: str | None = None
    nmc_consensus_text: str | None = None
    nmc_confidence: float = 0.0
    new_constitutional_hash: str | None = None
    deployed_at: datetime | None = None
    rejection_reason: str | None = None

    @classmethod
    def from_suggested_rule(cls, rule: "SuggestedRule") -> "GovernanceProposal":
        return cls(
            suggested_rule=rule,
            rule_text=rule.rule_text,
            rule_id=rule.rule_id,
            rationale=rule.rationale,
            confidence=rule.confidence,
        )

    def approve(self, new_hash: str) -> None:
        self.status = ProposalStatus.APPROVED
        self.new_constitutional_hash = new_hash
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, reason: str) -> None:
        self.status = ProposalStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def mark_deployed(self) -> None:
        self.status = ProposalStatus.DEPLOYED
        self.deployed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "rule_id": self.rule_id,
            "rule_text": self.rule_text,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "polis_statement_id": self.polis_statement_id,
            "polis_vote_count": self.polis_vote_count,
            "polis_consensus_score": self.polis_consensus_score,
            "nmc_session_id": self.nmc_session_id,
            "nmc_confidence": self.nmc_confidence,
            "new_constitutional_hash": self.new_constitutional_hash,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "rejection_reason": self.rejection_reason,
        }
