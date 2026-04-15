"""
ACGS-2 CCAI Democratic Framework - Governance Package
Constitutional Hash: 608508a9bd224290

This package provides the CCAI (Collective Constitutional AI) democratic governance
framework for constitutional AI governance with democratic deliberation.

Re-exports all public APIs from submodules for backward compatibility.

Modules:
    - models: Data models (Enums, dataclasses)
    - polis_engine: Polis-style deliberation engine
    - democratic_governance: Democratic constitutional governance framework

Constitutional Hash: 608508a9bd224290
"""

from .capability_passport import (
    CapabilityDomain,
    CapabilityPassport,
    DomainAutonomy,
    PassportRegistry,
    get_passport_registry,
    infer_domain,
    reset_passport_registry,
)
from .danger_signal import (
    AdaptiveQuorumDecision,
    AdaptiveQuorumMode,
    DangerSeverity,
    DangerSignal,
    DangerSignalAnalyzer,
)
from .democratic_governance import (
    DemocraticConstitutionalGovernance,
    ccai_governance,
    deliberate_on_proposal,
    get_ccai_governance,
)
from .governance_proposal import GovernanceProposal, ProposalStatus
from .loop_orchestrator import GovernanceLoopOrchestrator, get_orchestrator, reset_orchestrator
from .models import (
    CONSTITUTIONAL_HASH,
    ConstitutionalProposal,
    DeliberationPhase,
    DeliberationResult,
    DeliberationStatement,
    OpinionCluster,
    Stakeholder,
    StakeholderGroup,
)
from .polis_engine import PolisDeliberationEngine

__all__ = [
    "CapabilityDomain",
    "CapabilityPassport",
    "DomainAutonomy",
    "DangerSeverity",
    "DangerSignal",
    "DangerSignalAnalyzer",
    "AdaptiveQuorumMode",
    "AdaptiveQuorumDecision",
    "PassportRegistry",
    "get_passport_registry",
    "infer_domain",
    "CONSTITUTIONAL_HASH",
    "ConstitutionalProposal",
    "DeliberationPhase",
    "DeliberationResult",
    "DeliberationStatement",
    "DemocraticConstitutionalGovernance",
    "GovernanceLoopOrchestrator",
    "GovernanceProposal",
    "OpinionCluster",
    "PolisDeliberationEngine",
    "ProposalStatus",
    "Stakeholder",
    "StakeholderGroup",
    "ccai_governance",
    "deliberate_on_proposal",
    "get_ccai_governance",
    "get_orchestrator",
    "reset_orchestrator",
    "reset_passport_registry",
]
