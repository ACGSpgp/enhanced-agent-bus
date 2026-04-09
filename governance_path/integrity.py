"""Anti-bypass integrity checks for governance paths.

These helpers look for the common failure modes that a simple policy check does
not fully explain: broken signature chaining, absent required checkpoints,
backwards-moving timestamps, and constitutional hash mismatches. The result is a
structured error list suitable for fail-closed admission and auditing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import CheckpointType, GovernancePath
from .policy import MACIPathPolicy, RiskTier


@dataclass(slots=True)
class PathIntegrityError:
    """Structured integrity failure describing where a governance path breaks.

    Use this dataclass as a stable error payload when surfacing anti-bypass
    validation failures to logs, metrics, or higher-level enforcement layers.

    Invariants:
        - ``error_type`` is a machine-readable category string.
        - ``hop_index`` identifies the segment involved, or ``-1`` when the
          failure applies to the path as a whole.
        - ``detail`` is a human-readable explanation of the failure.
    """

    error_type: str
    hop_index: int
    detail: str


def check_signature_chain(path: GovernancePath, key: bytes) -> list[PathIntegrityError]:
    """Check that signatures form an unbroken hop-by-hop chain.

    Args:
        path: Governance path to validate.
        key: Shared HMAC key used to verify each segment signature.

    Returns:
        A list of signature-related integrity errors. The list is empty when the
        chain is intact.
    """
    errors: list[PathIntegrityError] = []

    for index, segment in enumerate(path.segments):
        expected_prev = "" if index == 0 else path.segments[index - 1].signature
        if segment.prev_signature != expected_prev:
            errors.append(
                PathIntegrityError(
                    error_type="SIGNATURE_GAP",
                    hop_index=index,
                    detail=(
                        f"Expected prev_signature {expected_prev!r}, "
                        f"found {segment.prev_signature!r}"
                    ),
                )
            )
            continue

        if not segment.verify(key, expected_prev):
            errors.append(
                PathIntegrityError(
                    error_type="SIGNATURE_GAP",
                    hop_index=index,
                    detail="Segment signature does not verify against the expected chain state",
                )
            )

    return errors


def check_required_checkpoints(
    path: GovernancePath,
    risk_tier: RiskTier,
) -> list[PathIntegrityError]:
    """Check that the path contains every checkpoint required for the risk tier.

    Args:
        path: Governance path to inspect.
        risk_tier: Risk tier that determines the required checkpoint set.

    Returns:
        A list of missing-checkpoint errors. The list is empty when all
        required checkpoints are present.
    """
    required = MACIPathPolicy.REQUIRED_CHECKPOINTS[risk_tier]
    present = {
        checkpoint
        for segment in path.segments
        for raw_check in segment.checks_performed
        for checkpoint in [CheckpointType.parse(raw_check)]
        if checkpoint is not None
    }

    return [
        PathIntegrityError(
            error_type="MISSING_HOP",
            hop_index=-1,
            detail=f"Missing required checkpoint: {checkpoint.name}",
        )
        for checkpoint in sorted(required - present, key=lambda item: item.name)
    ]


def check_temporal_ordering(
    path: GovernancePath,
    tolerance_seconds: float = 5.0,
) -> list[PathIntegrityError]:
    """Check that segment timestamps are monotonically increasing within tolerance.

    Args:
        path: Governance path to inspect.
        tolerance_seconds: Allowed backwards skew between adjacent timestamps.

    Returns:
        A list of temporal-ordering errors. The list is empty when timestamps do
        not move backwards beyond the configured tolerance.
    """
    errors: list[PathIntegrityError] = []

    for index in range(1, len(path.segments)):
        previous = path.segments[index - 1]
        current = path.segments[index]
        # Small clock skew is tolerated, but larger backwards jumps indicate
        # that the apparent processing order may have been tampered with.
        if current.timestamp + tolerance_seconds < previous.timestamp:
            errors.append(
                PathIntegrityError(
                    error_type="TEMPORAL_DISORDER",
                    hop_index=index,
                    detail=(
                        "Timestamp moved backwards beyond tolerance: "
                        f"{current.timestamp} < {previous.timestamp} - {tolerance_seconds}"
                    ),
                )
            )

    return errors


def check_constitutional_consistency(
    path: GovernancePath,
    expected_hash: str = "608508a9bd224290",
) -> list[PathIntegrityError]:
    """Check that every hop references the expected constitutional hash.

    Args:
        path: Governance path to inspect.
        expected_hash: Constitutional hash that every segment must carry.

    Returns:
        A list of constitutional-hash mismatch errors. The list is empty when
        every segment references the expected hash.
    """
    return [
        PathIntegrityError(
            error_type="HASH_MISMATCH",
            hop_index=index,
            detail=(
                f"Expected constitutional hash {expected_hash!r}, "
                f"found {segment.constitutional_hash!r}"
            ),
        )
        for index, segment in enumerate(path.segments)
        if segment.constitutional_hash != expected_hash
    ]


def full_integrity_check(
    path: GovernancePath,
    key: bytes,
    risk_tier: RiskTier,
    expected_hash: str = "608508a9bd224290",
    tolerance_seconds: float = 5.0,
) -> list[PathIntegrityError]:
    """Run the complete anti-bypass integrity suite for a governance path.

    Args:
        path: Governance path to validate.
        key: Shared HMAC key used for signature verification.
        risk_tier: Risk tier that determines required checkpoints.
        expected_hash: Constitutional hash that each segment must carry.
        tolerance_seconds: Allowed backwards skew between adjacent timestamps.

    Returns:
        A combined list of integrity errors from all anti-bypass checks.
    """
    return [
        *check_signature_chain(path, key),
        *check_required_checkpoints(path, risk_tier),
        *check_temporal_ordering(path, tolerance_seconds=tolerance_seconds),
        *check_constitutional_consistency(path, expected_hash=expected_hash),
    ]
