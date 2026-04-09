"""Federated governance primitives for cross-organizational agent governance.

This package exposes the federation surface used by the enhanced agent bus to
discover peers, establish bilateral trust, exchange privacy-preserving
governance summaries, and record tamper-evident audit trails. The public API is
organized around small, composable modules so transport code can combine peer
registration, handshakes, capability intersection, and policy-learning signals
without depending on raw constitutional rule text.

Key concepts:
    Federation peers advertise organization metadata and trust state.
    Handshakes use mutual HMAC challenge-response for fail-closed trust setup.
    Governance capability vectors summarize enforcement coverage without
        exposing rules, keywords, or patterns.
    Bilateral audit records preserve accountability for cross-org operations.
    Policy-learning signals share differentially private violation trends.

Constitutional Hash: 608508a9bd224290
"""

from .bilateral_audit import (
    BilateralAuditEntry,
    BilateralAuditLog,
    sign_bilateral_entry,
    verify_bilateral_signature,
)
from .handshake import FederationProtocol
from .intersection import (
    MergeSemantic,
    compute_capability_vector,
    compute_intersection,
)
from .models import (
    FederationHandshake,
    FederationPeer,
    GovernanceCapabilityVector,
    TrustLevel,
)
from .policy_learning import (
    AmendmentSuggestion,
    PolicyLearningChannel,
    ViolationSignal,
    apply_differential_privacy,
    compute_violation_signals,
    generate_amendment_suggestions,
)
from .registry import FederationRegistry

__all__ = [
    "AmendmentSuggestion",
    "BilateralAuditEntry",
    "BilateralAuditLog",
    "FederationHandshake",
    "FederationPeer",
    "FederationProtocol",
    "FederationRegistry",
    "GovernanceCapabilityVector",
    "MergeSemantic",
    "PolicyLearningChannel",
    "TrustLevel",
    "ViolationSignal",
    "apply_differential_privacy",
    "compute_capability_vector",
    "compute_intersection",
    "compute_violation_signals",
    "generate_amendment_suggestions",
    "sign_bilateral_entry",
    "verify_bilateral_signature",
]
