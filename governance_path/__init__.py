"""Public entrypoints for SCION-style governance-path routing.

The :mod:`enhanced_agent_bus.governance_path` package models a message route as
an authenticated chain of governance checkpoints. Each hop records which node
handled the message, which checks it performed, and an HMAC that binds the hop
to the previous signature. Higher-level helpers then validate policy
requirements, compute compact Merkle-root proofs, and detect anti-bypass
conditions such as missing checkpoints or reordered timestamps.
"""

from .integrity import (
    PathIntegrityError,
    check_constitutional_consistency,
    check_required_checkpoints,
    check_signature_chain,
    check_temporal_ordering,
    full_integrity_check,
)
from .models import CheckpointType, GovernancePath, PathSegment
from .policy import MACIPathPolicy
from .proof import (
    AggregatedProof,
    aggregate_proof,
    build_merkle_tree,
    decode_proof_header,
    encode_proof_header,
    inclusion_proof,
    verify_inclusion,
)
from .router import PathAwareRouter

__all__ = [
    "AggregatedProof",
    "CheckpointType",
    "GovernancePath",
    "MACIPathPolicy",
    "PathAwareRouter",
    "PathIntegrityError",
    "PathSegment",
    "aggregate_proof",
    "build_merkle_tree",
    "check_constitutional_consistency",
    "check_required_checkpoints",
    "check_signature_chain",
    "check_temporal_ordering",
    "decode_proof_header",
    "encode_proof_header",
    "full_integrity_check",
    "inclusion_proof",
    "verify_inclusion",
]
