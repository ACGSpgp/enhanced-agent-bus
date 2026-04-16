"""GovernanceLoopOrchestrator: bridges SuggestedRule → Polis → GovernanceProposal lifecycle."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acgs_lite.engine.synthesis import SynthesisReport

logger = logging.getLogger(__name__)


class GovernanceLoopOrchestrator:
    """Orchestrates the governance intelligence loop.

    Flow: AutoSynthesizer.synthesize() → submit_to_polis() → proposals
    Polis votes accumulate → approve/reject proposals
    Approved proposals → ConstitutionDeployer.deploy_approved_rules()
    """

    APPROVAL_POLIS_THRESHOLD: float = 0.6  # minimum consensus score to approve

    def __init__(self) -> None:
        self._proposals: dict[str, object] = {}  # proposal_id → GovernanceProposal
        self._polis: object | None = None  # lazy-loaded PolisDeliberationEngine
        self._polis_loaded: bool = False  # distinguishes "not tried" from "unavailable"

    def _get_polis(self) -> object | None:
        if not self._polis_loaded:
            self._polis_loaded = True
            try:
                from enhanced_agent_bus.governance.polis_engine import PolisDeliberationEngine

                self._polis = PolisDeliberationEngine()
            except Exception as exc:
                logger.warning("Polis engine unavailable: %s", type(exc).__name__)
                self._polis = None
        return self._polis

    def _make_system_stakeholder(self, author_id: str) -> object:
        """Create a system Stakeholder for automated submissions."""
        from enhanced_agent_bus.governance.models import Stakeholder, StakeholderGroup

        return Stakeholder(
            stakeholder_id=author_id,
            name="GovernanceLoopOrchestrator",
            group=StakeholderGroup.TECHNICAL_EXPERTS,
            expertise_areas=["governance", "synthesis"],
        )

    def ingest_synthesis_report(self, report: "SynthesisReport") -> list[object]:
        """Convert SynthesisReport.suggestions → GovernanceProposals and submit to Polis.

        Returns list of created GovernanceProposal objects.
        """
        from enhanced_agent_bus.governance.governance_proposal import GovernanceProposal

        created: list[GovernanceProposal] = []
        for suggestion in report.suggestions:
            proposal = GovernanceProposal.from_suggested_rule(suggestion)
            self._proposals[proposal.proposal_id] = proposal
            self._submit_to_polis(proposal)
            created.append(proposal)
            logger.info(
                "Created governance proposal proposal_id=%s rule_id=%s confidence=%s",
                proposal.proposal_id,
                proposal.rule_id,
                proposal.confidence,
            )
        return created

    def _submit_to_polis(self, proposal: object) -> None:
        """Submit a proposal to Polis for deliberation. Fails gracefully."""
        from enhanced_agent_bus.governance.governance_proposal import (
            GovernanceProposal,
            ProposalStatus,
        )

        if not isinstance(proposal, GovernanceProposal):
            raise TypeError(f"Expected GovernanceProposal, got {type(proposal).__name__}")

        polis = self._get_polis()
        if polis is None:
            logger.warning("Polis unavailable, proposal %s queued", proposal.proposal_id)
            return

        try:
            statement_id = self._call_polis_submit(polis, proposal.rule_text, proposal.proposal_id)
            proposal.polis_statement_id = statement_id
            proposal.status = ProposalStatus.DELIBERATING
            proposal.updated_at = datetime.datetime.now(datetime.timezone.utc)
        except Exception as exc:
            logger.warning(
                "Failed to submit proposal to Polis proposal_id=%s error=%s",
                proposal.proposal_id,
                type(exc).__name__,
            )

    def _call_polis_submit(self, polis: object, text: str, author_id: str) -> str:
        """Adapter: call PolisDeliberationEngine.submit_statement(content, author).

        submit_statement is async; we run it in a new event loop (or current one if available).
        Returns the statement_id from the resulting DeliberationStatement.
        """
        stakeholder = self._make_system_stakeholder(author_id)

        async def _submit() -> str:
            statement = await polis.submit_statement(text, stakeholder)  # type: ignore[union-attr]
            return statement.statement_id

        try:
            asyncio.get_running_loop()
            # We're already inside a running loop — schedule a concurrent task.
            # For sync callers in tests/CLI we fall back to asyncio.run().
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _submit())
                return future.result(timeout=10)
        except RuntimeError:
            # No running loop — safe to use asyncio.run().
            return asyncio.run(_submit())

    def list_proposals(self) -> list[dict]:
        return [p.to_dict() for p in self._proposals.values()]  # type: ignore[union-attr]

    def get_proposal(self, proposal_id: str) -> object | None:
        return self._proposals.get(proposal_id)

    def check_and_finalize(self) -> tuple[list[object], list[object]]:
        """Poll Polis consensus scores and approve/reject proposals that have reached threshold.

        Returns (approved_proposals, rejected_proposals).
        """
        from enhanced_agent_bus.governance.governance_proposal import (
            GovernanceProposal,
            ProposalStatus,
        )

        approved: list[object] = []
        rejected: list[object] = []
        for proposal in list(self._proposals.values()):
            if not isinstance(proposal, GovernanceProposal):
                continue  # skip corrupted entries rather than crash
            if proposal.status != ProposalStatus.DELIBERATING:
                continue
            score = self._get_polis_consensus(proposal)
            if score is None:
                continue
            proposal.polis_consensus_score = score
            if score >= self.APPROVAL_POLIS_THRESHOLD:
                proposal.status = ProposalStatus.CONSENSUS_REACHED
                approved.append(proposal)
            elif 0 < score < 0.3:  # actively rejected
                proposal.reject(f"Polis consensus score {score:.2f} below rejection threshold")
                rejected.append(proposal)
        return approved, rejected

    def _get_polis_consensus(self, proposal: object) -> float | None:
        """Get current consensus score from Polis for a proposal.

        Looks up the DeliberationStatement by polis_statement_id and returns
        its consensus_potential (range [-1, 1], shifted to [0, 1] for threshold checks).
        """
        from enhanced_agent_bus.governance.governance_proposal import GovernanceProposal

        if not isinstance(proposal, GovernanceProposal):
            raise TypeError(f"Expected GovernanceProposal, got {type(proposal).__name__}")
        if not proposal.polis_statement_id:
            return None

        polis = self._get_polis()
        if polis is None:
            return None

        statement = polis.statements.get(proposal.polis_statement_id)  # type: ignore[union-attr]
        if statement is None:
            return None

        # consensus_potential is in [-1, 1]; shift to [0, 1] so thresholds are intuitive.
        raw: float = statement.consensus_potential
        return (raw + 1.0) / 2.0


# Module-level singleton
_orchestrator: GovernanceLoopOrchestrator | None = None


def get_orchestrator() -> GovernanceLoopOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GovernanceLoopOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the module-level singleton. Use only in tests."""
    global _orchestrator
    _orchestrator = None
