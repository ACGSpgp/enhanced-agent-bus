"""Tests for GovernanceProposal state machine and lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from enhanced_agent_bus.governance.governance_proposal import GovernanceProposal, ProposalStatus

# ---------------------------------------------------------------------------
# Construction and defaults
# ---------------------------------------------------------------------------


def test_proposal_default_id_format() -> None:
    prop = GovernanceProposal()
    assert prop.proposal_id.startswith("PROP-")
    assert len(prop.proposal_id) == 13  # "PROP-" + 8 hex chars


def test_two_proposals_have_distinct_ids() -> None:
    p1 = GovernanceProposal()
    p2 = GovernanceProposal()
    assert p1.proposal_id != p2.proposal_id


def test_proposal_default_status_is_pending() -> None:
    prop = GovernanceProposal()
    assert prop.status == ProposalStatus.PENDING


def test_proposal_created_at_is_utc() -> None:
    prop = GovernanceProposal()
    assert prop.created_at.tzinfo is not None


def test_proposal_from_suggested_rule() -> None:
    rule = MagicMock()
    rule.rule_id = "SYNTH-099"
    rule.rule_text = "Never allow raw SQL injection"
    rule.rationale = "Security"
    rule.confidence = 0.95

    prop = GovernanceProposal.from_suggested_rule(rule)

    assert prop.rule_id == "SYNTH-099"
    assert prop.rule_text == "Never allow raw SQL injection"
    assert prop.rationale == "Security"
    assert prop.confidence == pytest.approx(0.95)
    assert prop.suggested_rule is rule
    assert prop.status == ProposalStatus.PENDING


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_approve_sets_status_and_hash() -> None:
    prop = GovernanceProposal(
        rule_id="R1", rule_text="rule", status=ProposalStatus.CONSENSUS_REACHED
    )
    prop.approve("newhash_abc123")
    assert prop.status == ProposalStatus.APPROVED
    assert prop.new_constitutional_hash == "newhash_abc123"


def test_approve_updates_updated_at() -> None:
    prop = GovernanceProposal(rule_id="R1", rule_text="rule")
    before = prop.updated_at
    prop.approve("hash")
    assert prop.updated_at >= before


def test_reject_sets_status_and_reason() -> None:
    prop = GovernanceProposal(rule_id="R2", rule_text="rule", status=ProposalStatus.DELIBERATING)
    prop.reject("Consensus score 0.12 below threshold")
    assert prop.status == ProposalStatus.REJECTED
    assert prop.rejection_reason == "Consensus score 0.12 below threshold"


def test_reject_updates_updated_at() -> None:
    prop = GovernanceProposal(rule_id="R2", rule_text="rule")
    before = prop.updated_at
    prop.reject("reason")
    assert prop.updated_at >= before


def test_mark_deployed_sets_status_and_deployed_at() -> None:
    prop = GovernanceProposal(rule_id="R3", rule_text="rule", status=ProposalStatus.APPROVED)
    prop.mark_deployed()
    assert prop.status == ProposalStatus.DEPLOYED
    assert prop.deployed_at is not None
    assert prop.deployed_at.tzinfo is not None


def test_mark_deployed_updates_updated_at() -> None:
    prop = GovernanceProposal(rule_id="R3", rule_text="rule")
    before = prop.updated_at
    prop.mark_deployed()
    assert prop.updated_at >= before


def test_full_lifecycle_pending_to_deployed() -> None:
    """Happy path: PENDING → DELIBERATING → CONSENSUS_REACHED → APPROVED → DEPLOYED."""
    prop = GovernanceProposal(rule_id="FULL", rule_text="rule")

    assert prop.status == ProposalStatus.PENDING

    prop.status = ProposalStatus.DELIBERATING
    prop.polis_statement_id = "STMT-001"
    assert prop.status == ProposalStatus.DELIBERATING

    prop.status = ProposalStatus.CONSENSUS_REACHED
    prop.polis_consensus_score = 0.72
    assert prop.status == ProposalStatus.CONSENSUS_REACHED

    prop.approve("hash_v2")
    assert prop.status == ProposalStatus.APPROVED
    assert prop.new_constitutional_hash == "hash_v2"

    prop.mark_deployed()
    assert prop.status == ProposalStatus.DEPLOYED
    assert prop.deployed_at is not None


def test_rejection_lifecycle_pending_to_rejected() -> None:
    prop = GovernanceProposal(rule_id="REJ", rule_text="rule", status=ProposalStatus.DELIBERATING)
    prop.polis_consensus_score = 0.08
    prop.reject("Polis consensus score 0.08 below rejection threshold")
    assert prop.status == ProposalStatus.REJECTED
    assert prop.rejection_reason is not None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_to_dict_keys_present() -> None:
    prop = GovernanceProposal(
        rule_id="DICT-1", rule_text="test", rationale="reason", confidence=0.5
    )
    d = prop.to_dict()

    required_keys = {
        "proposal_id",
        "rule_id",
        "rule_text",
        "rationale",
        "confidence",
        "status",
        "created_at",
        "updated_at",
        "polis_statement_id",
        "polis_vote_count",
        "polis_consensus_score",
        "nmc_session_id",
        "nmc_confidence",
        "new_constitutional_hash",
        "deployed_at",
        "rejection_reason",
    }
    assert required_keys.issubset(d.keys())


def test_to_dict_status_is_string() -> None:
    prop = GovernanceProposal(rule_id="DICT-2", rule_text="x")
    d = prop.to_dict()
    assert isinstance(d["status"], str)
    assert d["status"] == "pending"


def test_to_dict_deployed_at_none_before_deploy() -> None:
    prop = GovernanceProposal(rule_id="DICT-3", rule_text="x")
    assert prop.to_dict()["deployed_at"] is None


def test_to_dict_deployed_at_iso_after_deploy() -> None:
    prop = GovernanceProposal(rule_id="DICT-4", rule_text="x")
    prop.mark_deployed()
    deployed_at = prop.to_dict()["deployed_at"]
    assert isinstance(deployed_at, str)
    # Should be parseable as ISO datetime
    parsed = datetime.fromisoformat(deployed_at)
    assert parsed.tzinfo is not None


def test_to_dict_confidence_float() -> None:
    prop = GovernanceProposal(rule_id="DICT-5", rule_text="x", confidence=0.87)
    assert prop.to_dict()["confidence"] == pytest.approx(0.87)


# ---------------------------------------------------------------------------
# ProposalStatus enum
# ---------------------------------------------------------------------------


def test_all_statuses_are_string_values() -> None:
    for status in ProposalStatus:
        assert isinstance(status.value, str)


def test_status_string_equality() -> None:
    assert ProposalStatus.PENDING == "pending"
    assert ProposalStatus.DELIBERATING == "deliberating"
    assert ProposalStatus.CONSENSUS_REACHED == "consensus_reached"
    assert ProposalStatus.APPROVED == "approved"
    assert ProposalStatus.REJECTED == "rejected"
    assert ProposalStatus.DEPLOYED == "deployed"
