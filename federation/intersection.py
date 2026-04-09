"""Capability-vector summarization and intersection semantics for federation.

This module turns local governance rules into a privacy-preserving capability
vector, then combines two vectors to estimate the governance envelope for a
cross-organization interaction. The intersection logic operates only on
normalized categories and severities so raw rule text never leaves its source
organization.

Key concepts:
    Capability vectors retain coverage shape, not rule internals.
    Merge semantics control whether local policy dominates or the strictest
        shared posture is enforced.
    Metadata joins preserve provenance without affecting category severity.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from enum import Enum

from .models import GovernanceCapabilityVector

SEVERITY_ORDER = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


class MergeSemantic(Enum):
    """Strategies for combining two governance capability vectors.

    Use this enum when deciding how a local organization should reconcile its
    governance coverage with a peer's advertised coverage. The default strictest
    mode is appropriate for fail-closed federation, while local override exists
    for explicitly asymmetric trust models.

    Invariants:
        Enum values are stable transport identifiers.
        ``STRICTEST_WINS`` and ``UNION`` currently share the same severity merge
        behavior for overlapping categories.
    """

    STRICTEST_WINS = "strictest_wins"
    LOCAL_OVERRIDE = "local_override"
    UNION = "union"


def compute_capability_vector(
    rules: list[object],
    org_id: str = "",
    version: str = "1.0",
) -> GovernanceCapabilityVector:
    """Summarize active governance rules into a category-severity vector.

    Args:
        rules: Rule-like objects with ``category``, ``severity``, and optional
            ``active`` attributes.
        org_id: Organization identifier to attach as vector metadata.
        version: Schema or policy version to attach as vector metadata.

    Returns:
        GovernanceCapabilityVector: Privacy-preserving summary of active rule
        coverage.

    Raises:
        ValueError: If a rule exposes an unsupported severity label.
    """

    category_severities: dict[str, str] = {}
    total_rules = 0

    for rule in rules:
        if not _is_active(rule):
            continue
        category = _normalize_category(getattr(rule, "category", ""))
        severity = _normalize_severity(getattr(rule, "severity", ""))
        if not category:
            continue
        total_rules += 1
        # Keep only the strongest severity per category so the vector exposes
        # coverage shape without leaking individual rule count or text.
        current = category_severities.get(category)
        if current is None or SEVERITY_ORDER[severity] > SEVERITY_ORDER[current]:
            category_severities[category] = severity

    return GovernanceCapabilityVector(
        category_severities=category_severities,
        total_rules=total_rules,
        version=version,
        org_id=org_id,
    )


def compute_intersection(
    local: GovernanceCapabilityVector,
    peer: GovernanceCapabilityVector,
    semantic: MergeSemantic,
) -> GovernanceCapabilityVector:
    """Merge two capability vectors according to the selected semantic.

    Args:
        local: Capability vector for the local organization.
        peer: Capability vector advertised by the remote organization.
        semantic: Merge policy controlling how overlapping categories are
            reconciled.

    Returns:
        GovernanceCapabilityVector: Combined coverage summary for bilateral
        federation decisions.

    Raises:
        None.
    """

    if semantic is MergeSemantic.LOCAL_OVERRIDE:
        return local

    merged_categories = set(local.category_severities) | set(peer.category_severities)
    category_severities: dict[str, str] = {}
    for category in sorted(merged_categories):
        local_severity = local.category_severities.get(category)
        peer_severity = peer.category_severities.get(category)
        if local_severity is None:
            category_severities[category] = peer_severity  # type: ignore[assignment]
            continue
        if peer_severity is None:
            category_severities[category] = local_severity
            continue
        # Intersection semantics are fail-closed for overlaps: both parties must
        # honor the stricter category severity before traffic is allowed.
        category_severities[category] = _higher_severity(local_severity, peer_severity)

    return GovernanceCapabilityVector(
        category_severities=category_severities,
        total_rules=local.total_rules + peer.total_rules,
        version=_merge_metadata(local.version, peer.version),
        org_id=_merge_metadata(local.org_id, peer.org_id),
    )


def _is_active(rule: object) -> bool:
    active = getattr(rule, "active", True)
    return bool(active)


def _normalize_category(category: object) -> str:
    return str(category).strip().lower()


def _normalize_severity(severity: object) -> str:
    normalized = str(severity).strip().upper()
    if normalized not in SEVERITY_ORDER:
        raise ValueError(f"unsupported severity: {severity}")
    return normalized


def _higher_severity(left: str, right: str) -> str:
    if SEVERITY_ORDER[left] >= SEVERITY_ORDER[right]:
        return left
    return right


def _merge_metadata(left: str, right: str) -> str:
    values = sorted({value for value in (left, right) if value})
    return "|".join(values)


__all__ = [
    "SEVERITY_ORDER",
    "MergeSemantic",
    "compute_capability_vector",
    "compute_intersection",
]
