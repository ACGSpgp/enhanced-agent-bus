"""Tests for SCION-style path-aware governance routing."""

from __future__ import annotations

from enhanced_agent_bus.governance_path import (
    CheckpointType,
    GovernancePath,
    MACIPathPolicy,
    PathSegment,
)
from enhanced_agent_bus.governance_path.policy import RiskTier

TEST_KEY = b"governance-path-test-key"
CONSTITUTIONAL_HASH = "608508a9bd224290"


def _segment(
    *checks: CheckpointType, node_id: str = "node-1", node_role: str = "EXECUTIVE"
) -> PathSegment:
    return PathSegment(
        node_id=node_id,
        node_role=node_role,
        constitutional_hash=CONSTITUTIONAL_HASH,
        checks_performed=frozenset(check.value for check in checks),
    )


def _signed_path(*segments: PathSegment) -> GovernancePath:
    prev_sig = ""
    for segment in segments:
        prev_sig = segment.sign(TEST_KEY, prev_sig)
    return GovernancePath(segments=list(segments))


def test_segment_sign_and_verify() -> None:
    segment = _segment(CheckpointType.CONSTITUTIONAL_HASH)

    signature = segment.sign(TEST_KEY, "")

    assert signature == segment.signature
    assert segment.prev_signature == ""
    assert segment.verify(TEST_KEY, "")


def test_segment_tamper_detection() -> None:
    segment = _segment(CheckpointType.CONSTITUTIONAL_HASH, node_id="origin")
    segment.sign(TEST_KEY, "")
    segment.node_id = "tampered"

    assert not segment.verify(TEST_KEY, "")


def test_chain_3_hops() -> None:
    path = _signed_path(
        _segment(CheckpointType.CONSTITUTIONAL_HASH, node_id="ingress"),
        _segment(CheckpointType.MACI_ROLE_CHECK, node_id="validator"),
        _segment(CheckpointType.FULL_VALIDATION, node_id="egress"),
    )

    assert path.verify_chain(TEST_KEY)


def test_chain_tampered_middle_hop() -> None:
    first = _segment(CheckpointType.CONSTITUTIONAL_HASH, node_id="ingress")
    second = _segment(CheckpointType.MACI_ROLE_CHECK, node_id="validator")
    third = _segment(CheckpointType.FULL_VALIDATION, node_id="egress")
    path = _signed_path(first, second, third)
    second.checks_performed = frozenset(
        {
            CheckpointType.MACI_ROLE_CHECK.value,
            CheckpointType.IMPACT_SCORING.value,
        }
    )

    assert not path.verify_chain(TEST_KEY)


def test_ordering_valid() -> None:
    path = GovernancePath(
        segments=[
            _segment(CheckpointType.CONSTITUTIONAL_HASH),
            _segment(CheckpointType.MACI_ROLE_CHECK),
            _segment(CheckpointType.IMPACT_SCORING),
            _segment(CheckpointType.FULL_VALIDATION),
            _segment(CheckpointType.HUMAN_REVIEW),
        ]
    )

    assert path.validate_ordering() == (True, None)


def test_ordering_invalid() -> None:
    path = GovernancePath(
        segments=[
            _segment(CheckpointType.FULL_VALIDATION),
            _segment(CheckpointType.CONSTITUTIONAL_HASH),
        ]
    )

    assert path.validate_ordering() == (
        False,
        "CONSTITUTIONAL_HASH must appear before FULL_VALIDATION",
    )


def test_policy_low_any_path() -> None:
    policy = MACIPathPolicy()
    path = GovernancePath(segments=[_segment(CheckpointType.FULL_VALIDATION)])

    assert policy.validate_path(path, RiskTier.LOW) == (True, None)


def test_policy_medium_requires_role_check() -> None:
    policy = MACIPathPolicy()
    path = GovernancePath(segments=[_segment(CheckpointType.CONSTITUTIONAL_HASH)])

    assert policy.validate_path(path, RiskTier.MEDIUM) == (
        False,
        "Missing required checkpoints: MACI_ROLE_CHECK",
    )


def test_policy_critical_missing_human_review() -> None:
    policy = MACIPathPolicy()
    path = GovernancePath(
        segments=[
            _segment(CheckpointType.MACI_ROLE_CHECK),
            _segment(CheckpointType.IMPACT_SCORING),
        ]
    )

    assert policy.validate_path(path, RiskTier.CRITICAL) == (
        False,
        "Missing required checkpoints: HUMAN_REVIEW",
    )


def test_empty_path_backward_compatible() -> None:
    path = GovernancePath()
    policy = MACIPathPolicy()

    assert path.verify_chain(TEST_KEY)
    assert path.validate_ordering() == (True, None)
    assert policy.validate_path(path, RiskTier.LOW) == (True, None)


def test_serialization_roundtrip() -> None:
    original = _signed_path(
        _segment(CheckpointType.CONSTITUTIONAL_HASH, node_id="ingress"),
        _segment(CheckpointType.MACI_ROLE_CHECK, node_id="validator", node_role="JUDICIAL"),
    )

    restored = GovernancePath.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()
    assert restored.verify_chain(TEST_KEY)


from hashlib import sha256

from enhanced_agent_bus.governance_path import (
    aggregate_proof,
    build_merkle_tree,
    check_constitutional_consistency,
    check_required_checkpoints,
    check_signature_chain,
    check_temporal_ordering,
    decode_proof_header,
    encode_proof_header,
    full_integrity_check,
    inclusion_proof,
    verify_inclusion,
)


def _valid_hops(*checkpoint_groups: tuple[CheckpointType, ...]) -> GovernancePath:
    segments: list[PathSegment] = []
    prev_sig = ""
    base_timestamp = 1_700_000_000.0

    for index, checkpoints in enumerate(checkpoint_groups):
        segment = _segment(
            *checkpoints,
            node_id=f"node-{index + 1}",
            node_role="GOVERNANCE",
        )
        segment.timestamp = base_timestamp + (index * 10.0)
        prev_sig = segment.sign(TEST_KEY, prev_sig)
        segments.append(segment)

    return GovernancePath(segments=segments)


def test_merkle_tree_single_segment() -> None:
    path = _valid_hops((CheckpointType.CONSTITUTIONAL_HASH,))

    tree = build_merkle_tree(path.segments)

    assert len(tree) == 1


def test_merkle_tree_three_segments() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )

    tree = build_merkle_tree(path.segments)

    assert len(tree) == 6


def test_aggregate_proof_matches_tree_root() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.HUMAN_REVIEW,),
    )

    proof = aggregate_proof(path)

    assert proof.merkle_root == build_merkle_tree(path.segments)[-1]


def test_inclusion_proof_valid() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )
    tree = build_merkle_tree(path.segments)
    proof_pairs = inclusion_proof(tree, 0, len(path.segments))
    leaf_hash = sha256(path.segments[0].signature.encode("utf-8")).hexdigest()

    assert verify_inclusion(leaf_hash, proof_pairs, tree[-1])


def test_inclusion_proof_wrong_root_fails() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )
    tree = build_merkle_tree(path.segments)
    proof_pairs = inclusion_proof(tree, 0, len(path.segments))
    leaf_hash = sha256(path.segments[0].signature.encode("utf-8")).hexdigest()

    assert not verify_inclusion(leaf_hash, proof_pairs, "0" * 64)


def test_proof_header_encode_decode_roundtrip() -> None:
    proof = aggregate_proof(
        _valid_hops(
            (CheckpointType.CONSTITUTIONAL_HASH,),
            (CheckpointType.MACI_ROLE_CHECK,),
        )
    )

    restored = decode_proof_header(encode_proof_header(proof))

    assert restored.to_dict() == proof.to_dict()


def test_signature_chain_valid() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )

    assert check_signature_chain(path, TEST_KEY) == []


def test_signature_gap_detected() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )
    path.segments[1].signature = "deadbeef"

    errors = check_signature_chain(path, TEST_KEY)

    assert any(error.error_type == "SIGNATURE_GAP" for error in errors)


def test_missing_checkpoint_detected() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.IMPACT_SCORING,),
    )

    errors = check_required_checkpoints(path, RiskTier.CRITICAL)

    assert errors == [
        errors[0].__class__(
            error_type="MISSING_HOP",
            hop_index=-1,
            detail="Missing required checkpoint: HUMAN_REVIEW",
        )
    ]


def test_temporal_disorder_detected() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.FULL_VALIDATION,),
    )
    path.segments[2].timestamp = path.segments[1].timestamp - 10.0

    errors = check_temporal_ordering(path)

    assert any(error.error_type == "TEMPORAL_DISORDER" for error in errors)


def test_constitutional_hash_mismatch() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.HUMAN_REVIEW,),
    )
    path.segments[1].constitutional_hash = "wrong-hash"

    errors = check_constitutional_consistency(path)

    assert any(error.error_type == "HASH_MISMATCH" for error in errors)


def test_full_integrity_check_clean() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.IMPACT_SCORING,),
        (CheckpointType.HUMAN_REVIEW,),
    )

    assert full_integrity_check(path, TEST_KEY, RiskTier.CRITICAL) == []


def test_full_integrity_check_multiple_errors() -> None:
    path = _valid_hops(
        (CheckpointType.CONSTITUTIONAL_HASH,),
        (CheckpointType.MACI_ROLE_CHECK,),
        (CheckpointType.IMPACT_SCORING,),
    )
    path.segments[2].timestamp = path.segments[1].timestamp - 10.0

    errors = full_integrity_check(path, TEST_KEY, RiskTier.CRITICAL)

    assert len(errors) == 2
