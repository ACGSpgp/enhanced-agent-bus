"""Tests for GovernanceLoopOrchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from enhanced_agent_bus.governance.governance_proposal import GovernanceProposal, ProposalStatus
from enhanced_agent_bus.governance.loop_orchestrator import (
    GovernanceLoopOrchestrator,
    get_orchestrator,
    reset_orchestrator,
)


def _make_suggested_rule(rule_id: str = "SYNTH-001", confidence: float = 0.8) -> MagicMock:
    """Create a minimal SuggestedRule-like object."""
    rule = MagicMock()
    rule.rule_id = rule_id
    rule.rule_text = f"Test rule {rule_id}"
    rule.rationale = "Test rationale"
    rule.confidence = confidence
    rule.severity = MagicMock()
    rule.category = "test"
    rule.keywords = ["test"]
    return rule


def _make_synthesis_report(rules: list) -> MagicMock:
    report = MagicMock()
    report.suggestions = rules
    return report


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def test_ingest_synthesis_report_creates_proposals() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True  # skip lazy load

    rule = _make_suggested_rule()
    proposals = orch.ingest_synthesis_report(_make_synthesis_report([rule]))

    assert len(proposals) == 1
    assert proposals[0].rule_id == "SYNTH-001"


def test_ingest_without_polis_does_not_crash() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True

    rule = _make_suggested_rule("SYNTH-002", confidence=0.7)
    proposals = orch.ingest_synthesis_report(_make_synthesis_report([rule]))

    assert len(proposals) == 1
    # No polis_statement_id set because Polis was unavailable
    assert proposals[0].polis_statement_id is None


def test_ingest_multiple_rules_all_become_proposals() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True

    rules = [_make_suggested_rule(f"SYNTH-{i:03d}") for i in range(5)]
    proposals = orch.ingest_synthesis_report(_make_synthesis_report(rules))

    assert len(proposals) == 5
    ids = {p.rule_id for p in proposals}
    assert ids == {f"SYNTH-{i:03d}" for i in range(5)}


def test_ingest_stores_proposals_internally() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True

    rule = _make_suggested_rule()
    proposals = orch.ingest_synthesis_report(_make_synthesis_report([rule]))

    assert orch.get_proposal(proposals[0].proposal_id) is proposals[0]


# ---------------------------------------------------------------------------
# Polis submission
# ---------------------------------------------------------------------------


def test_submit_to_polis_sets_statement_id() -> None:
    """When Polis is available, submission sets polis_statement_id and DELIBERATING status."""
    orch = GovernanceLoopOrchestrator()

    fake_statement = MagicMock()
    fake_statement.statement_id = "STMT-abc123"
    fake_polis = MagicMock()

    import asyncio

    async def _fake_submit(content: str, author: object) -> MagicMock:
        return fake_statement

    fake_polis.submit_statement.side_effect = _fake_submit
    orch._polis = fake_polis
    orch._polis_loaded = True

    rule = _make_suggested_rule()
    proposals = orch.ingest_synthesis_report(_make_synthesis_report([rule]))

    assert proposals[0].polis_statement_id == "STMT-abc123"
    assert proposals[0].status == ProposalStatus.DELIBERATING


# ---------------------------------------------------------------------------
# check_and_finalize
# ---------------------------------------------------------------------------


def test_check_and_finalize_approves_high_score() -> None:
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(
        rule_id="SYNTH-003",
        rule_text="Rule",
        status=ProposalStatus.DELIBERATING,
        polis_statement_id="STMT-1",
    )
    orch._proposals[prop.proposal_id] = prop

    orch._get_polis_consensus = lambda p: 0.75  # type: ignore[method-assign]

    approved, rejected = orch.check_and_finalize()

    assert len(approved) == 1
    assert approved[0].status == ProposalStatus.CONSENSUS_REACHED
    assert len(rejected) == 0


def test_check_and_finalize_rejects_low_score() -> None:
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(
        rule_id="SYNTH-004",
        rule_text="Rule",
        status=ProposalStatus.DELIBERATING,
        polis_statement_id="STMT-2",
    )
    orch._proposals[prop.proposal_id] = prop

    orch._get_polis_consensus = lambda p: 0.1  # type: ignore[method-assign]

    approved, rejected = orch.check_and_finalize()

    assert len(rejected) == 1
    assert rejected[0].status == ProposalStatus.REJECTED
    assert len(approved) == 0


def test_check_and_finalize_skips_non_deliberating() -> None:
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(
        rule_id="SYNTH-005",
        rule_text="Rule",
        status=ProposalStatus.APPROVED,
    )
    orch._proposals[prop.proposal_id] = prop
    orch._get_polis_consensus = lambda p: 0.9  # type: ignore[method-assign]

    approved, rejected = orch.check_and_finalize()

    assert len(approved) == 0
    assert len(rejected) == 0


def test_check_and_finalize_skips_none_score() -> None:
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(
        rule_id="SYNTH-006",
        rule_text="Rule",
        status=ProposalStatus.DELIBERATING,
    )
    orch._proposals[prop.proposal_id] = prop
    orch._get_polis_consensus = lambda p: None  # type: ignore[method-assign]

    approved, rejected = orch.check_and_finalize()

    assert len(approved) == 0
    assert len(rejected) == 0


def test_check_and_finalize_middle_score_no_action() -> None:
    """Score in (0.3, 0.6) — neither approved nor rejected yet."""
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(
        rule_id="SYNTH-007",
        rule_text="Rule",
        status=ProposalStatus.DELIBERATING,
    )
    orch._proposals[prop.proposal_id] = prop
    orch._get_polis_consensus = lambda p: 0.45  # type: ignore[method-assign]

    approved, rejected = orch.check_and_finalize()

    assert len(approved) == 0
    assert len(rejected) == 0
    # polis_consensus_score was still updated
    assert prop.polis_consensus_score == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# list_proposals
# ---------------------------------------------------------------------------


def test_list_proposals_returns_dicts() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True

    rule = _make_suggested_rule()
    orch.ingest_synthesis_report(_make_synthesis_report([rule]))

    listed = orch.list_proposals()

    assert len(listed) == 1
    assert "proposal_id" in listed[0]
    assert "rule_text" in listed[0]


def test_list_proposals_empty_initially() -> None:
    orch = GovernanceLoopOrchestrator()
    assert orch.list_proposals() == []


# ---------------------------------------------------------------------------
# _get_polis_consensus via real statements dict
# ---------------------------------------------------------------------------


def test_get_polis_consensus_returns_shifted_score() -> None:
    """consensus_potential=-1..1 is shifted to 0..1."""
    orch = GovernanceLoopOrchestrator()

    fake_stmt = MagicMock()
    fake_stmt.consensus_potential = 0.2  # raw → shifted = (0.2+1)/2 = 0.6
    fake_polis = MagicMock()
    fake_polis.statements = {"STMT-X": fake_stmt}
    orch._polis = fake_polis
    orch._polis_loaded = True

    prop = GovernanceProposal(rule_id="R1", rule_text="r", polis_statement_id="STMT-X")
    score = orch._get_polis_consensus(prop)

    assert score == pytest.approx(0.6)


def test_get_polis_consensus_no_statement_id_returns_none() -> None:
    orch = GovernanceLoopOrchestrator()
    prop = GovernanceProposal(rule_id="R2", rule_text="r", polis_statement_id=None)
    assert orch._get_polis_consensus(prop) is None


def test_get_polis_consensus_missing_statement_returns_none() -> None:
    orch = GovernanceLoopOrchestrator()
    fake_polis = MagicMock()
    fake_polis.statements = {}
    orch._polis = fake_polis
    orch._polis_loaded = True

    prop = GovernanceProposal(rule_id="R3", rule_text="r", polis_statement_id="STMT-MISSING")
    assert orch._get_polis_consensus(prop) is None


# ---------------------------------------------------------------------------
# TypeError guards (assert → isinstance was fixed; these pin the behavior)
# ---------------------------------------------------------------------------


def test_submit_to_polis_raises_type_error_for_non_proposal() -> None:
    orch = GovernanceLoopOrchestrator()
    fake_polis = MagicMock()
    orch._polis = fake_polis
    orch._polis_loaded = True

    with pytest.raises(TypeError, match="GovernanceProposal"):
        orch._submit_to_polis("this is not a GovernanceProposal")


def test_get_polis_consensus_raises_type_error_for_non_proposal() -> None:
    orch = GovernanceLoopOrchestrator()
    with pytest.raises(TypeError, match="GovernanceProposal"):
        orch._get_polis_consensus({"not": "a proposal"})


def test_check_and_finalize_skips_corrupted_entry() -> None:
    """Non-GovernanceProposal entry in _proposals is silently skipped."""
    orch = GovernanceLoopOrchestrator()
    orch._proposals["corrupt-key"] = "not a proposal"

    # Should not raise
    approved, rejected = orch.check_and_finalize()
    assert approved == []
    assert rejected == []


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def test_get_orchestrator_returns_singleton() -> None:
    reset_orchestrator()
    o1 = get_orchestrator()
    o2 = get_orchestrator()
    assert o1 is o2


def test_reset_orchestrator_clears_state() -> None:
    reset_orchestrator()
    orch = get_orchestrator()
    orch._polis = None
    orch._polis_loaded = True
    rule = _make_suggested_rule("RESET-001")
    orch.ingest_synthesis_report(_make_synthesis_report([rule]))
    assert len(orch.list_proposals()) == 1

    reset_orchestrator()
    fresh = get_orchestrator()
    assert len(fresh.list_proposals()) == 0


# ---------------------------------------------------------------------------
# get_proposal
# ---------------------------------------------------------------------------


def test_get_proposal_returns_none_for_unknown_id() -> None:
    orch = GovernanceLoopOrchestrator()
    assert orch.get_proposal("PROP-DOESNOTEXIST") is None


def test_get_proposal_returns_proposal_after_ingest() -> None:
    orch = GovernanceLoopOrchestrator()
    orch._polis = None
    orch._polis_loaded = True
    rule = _make_suggested_rule("SYNTH-GET")
    proposals = orch.ingest_synthesis_report(_make_synthesis_report([rule]))
    pid = proposals[0].proposal_id
    assert orch.get_proposal(pid) is proposals[0]


# ---------------------------------------------------------------------------
# APPROVAL_POLIS_THRESHOLD is in spec
# ---------------------------------------------------------------------------


def test_approval_threshold_matches_spec() -> None:
    """Approval threshold must be 0.6 per spec."""
    assert GovernanceLoopOrchestrator.APPROVAL_POLIS_THRESHOLD == pytest.approx(0.6)
