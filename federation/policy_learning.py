"""Privacy-preserving policy-learning signals for federated governance.

This module aggregates raw local violations into coarse-grained learning
signals, optionally applies differential privacy, and turns high-signal peer
observations into bounded constitutional amendment suggestions. The design keeps
federation traffic focused on aggregate category trends rather than matched
content, rule identifiers, or other sensitive enforcement details.

Key concepts:
    Violation signals summarize category, severity, frequency, and trend only.
    Differential privacy perturbs frequency buckets to reduce re-identification
        risk.
    Amendment suggestions cap peer influence so local governance remains
        primary.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import asyncio
import math
import random
from collections import defaultdict
from dataclasses import dataclass

from .intersection import SEVERITY_ORDER
from .models import GovernanceCapabilityVector

FREQUENCY_BUCKETS = ("none", "low", "medium", "high")


@dataclass(slots=True)
class _SignalAggregate:
    """Intermediate aggregate used while generating amendment suggestions.

    Use this helper only inside this module while combining multiple peer
    signals by category. It tracks the strongest observed severity, unique peer
    contributors, and coarse trend directions.

    Invariants:
        ``severity`` is always a valid key in ``SEVERITY_ORDER``.
        ``org_ids`` contains unique non-empty organization identifiers only.
        ``trends`` stores normalized trend labels gathered from peer signals.
    """

    severity: str
    org_ids: set[str]
    trends: set[str]


@dataclass(frozen=True, slots=True)
class ViolationSignal:
    """Privacy-preserving summary of a violation cohort.

    Use this dataclass to exchange learning-oriented federation telemetry
    without disclosing matched content, rule identifiers, or underlying
    evidence. Each signal captures only coarse category, severity, frequency,
    and trend information for a time window.

    Invariants:
        ``frequency_bucket`` is one of ``FREQUENCY_BUCKETS``.
        ``severity`` should map to a supported governance severity.
        Window bounds are coarse metadata and may be zero when unavailable.
    """

    category: str
    severity: str
    frequency_bucket: str
    temporal_trend: str
    org_id: str = ""
    window_start: float = 0.0
    window_end: float = 0.0

    def to_dict(self) -> dict[str, str | float]:
        """Serialize the signal to a plain dictionary.

        Args:
            None.

        Returns:
            dict[str, str | float]: JSON-serializable signal data.

        Raises:
            None.
        """

        return {
            "category": self.category,
            "severity": self.severity,
            "frequency_bucket": self.frequency_bucket,
            "temporal_trend": self.temporal_trend,
            "org_id": self.org_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ViolationSignal:
        """Deserialize a signal from a plain dictionary.

        Args:
            data: Serialized signal payload produced by :meth:`to_dict` or an
                equivalent transport envelope.

        Returns:
            ViolationSignal: Reconstructed privacy-preserving signal.

        Raises:
            KeyError: If a required signal field is missing.
            ValueError: If window bounds cannot be converted to ``float``.
        """

        return cls(
            category=str(data["category"]),
            severity=str(data["severity"]),
            frequency_bucket=str(data["frequency_bucket"]),
            temporal_trend=str(data["temporal_trend"]),
            org_id=str(data.get("org_id", "")),
            window_start=float(data.get("window_start", 0.0)),
            window_end=float(data.get("window_end", 0.0)),
        )


def compute_violation_signals(
    violations: list[dict[str, object]], window_hours: float = 24.0
) -> list[ViolationSignal]:
    """Aggregate raw violations into privacy-preserving learning signals.

    Args:
        violations: Raw violation dictionaries containing category, severity,
            and timestamp-like fields.
        window_hours: Width of the rolling aggregation window in hours.

    Returns:
        list[ViolationSignal]: Aggregated signals for valid category and
        severity cohorts within the window.

    Raises:
        None.
    """

    if not violations:
        return []

    timestamps = [float(violation.get("timestamp", 0.0)) for violation in violations]
    window_end = max(timestamps)
    window_start = max(window_end - (window_hours * 3600.0), min(timestamps))
    midpoint = window_start + ((window_end - window_start) / 2.0)

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for violation in violations:
        timestamp = float(violation.get("timestamp", 0.0))
        if timestamp < window_start or timestamp > window_end:
            continue
        category = str(violation.get("category", "")).strip().lower()
        severity = str(violation.get("severity", "")).strip().upper()
        if not category or severity not in SEVERITY_ORDER:
            continue
        grouped[(category, severity)].append(timestamp)

    signals: list[ViolationSignal] = []
    for (category, severity), group_timestamps in sorted(grouped.items()):
        count = len(group_timestamps)
        first_half = sum(1 for timestamp in group_timestamps if timestamp < midpoint)
        second_half = count - first_half
        signals.append(
            ViolationSignal(
                category=category,
                severity=severity,
                frequency_bucket=_bucket_for_count(count),
                temporal_trend=_compute_trend(first_half, second_half),
                window_start=window_start,
                window_end=window_end,
            )
        )
    return signals


def apply_differential_privacy(
    signals: list[ViolationSignal], epsilon: float = 1.0
) -> list[ViolationSignal]:
    """Return differentially private copies of violation signals.

    Args:
        signals: Signals whose frequency buckets should be privacy-protected.
        epsilon: Differential privacy parameter. Lower values introduce more
            noise, while high values approach the original buckets.

    Returns:
        list[ViolationSignal]: New signals with privacy-adjusted frequency
        buckets.

    Raises:
        None.
    """

    if not signals:
        return []

    safe_epsilon = max(epsilon, 0.001)
    if safe_epsilon >= 5.0:
        return [
            ViolationSignal(
                category=signal.category,
                severity=signal.severity,
                frequency_bucket=signal.frequency_bucket,
                temporal_trend=signal.temporal_trend,
                org_id=signal.org_id,
                window_start=signal.window_start,
                window_end=signal.window_end,
            )
            for signal in signals
        ]

    rng = random.Random(_seed_for_signals(signals, safe_epsilon))
    flip_probability = min(0.5, 1.0 / (safe_epsilon * 4.0))

    privatized: list[ViolationSignal] = []
    for signal in signals:
        bucket_index = _bucket_index(signal.frequency_bucket)
        # Add Laplace noise in bucket space so peers learn coarse prevalence
        # without being able to reconstruct exact local violation counts.
        noisy_index = round(bucket_index + _laplace_noise(rng, 1.0 / safe_epsilon))
        noisy_index = max(0, min(noisy_index, len(FREQUENCY_BUCKETS) - 1))

        # A small random neighbor flip reduces deterministic reconstruction from
        # repeated queries against the same underlying cohort.
        if rng.random() < flip_probability:
            direction = -1 if rng.random() < 0.5 else 1
            noisy_index = max(0, min(noisy_index + direction, len(FREQUENCY_BUCKETS) - 1))

        privatized.append(
            ViolationSignal(
                category=signal.category,
                severity=signal.severity,
                frequency_bucket=FREQUENCY_BUCKETS[noisy_index],
                temporal_trend=signal.temporal_trend,
                org_id=signal.org_id,
                window_start=signal.window_start,
                window_end=signal.window_end,
            )
        )
    return privatized


class PolicyLearningChannel:
    """Async-safe in-memory channel for federated learning signals.

    Use this class to stage outbound and inbound batches of privacy-preserving
    signals during tests or lightweight federation flows. It models the
    interface that a transport-backed signal bus would expose without embedding
    transport concerns in the learning logic.

    Invariants:
        Published and received batches are copied before storage.
        Disabling the channel fail-closes publication attempts.
        All queue mutations occur under ``_lock``.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._published: list[list[ViolationSignal]] = []
        self._received: list[list[ViolationSignal]] = []
        self.enabled = enabled
        self._lock = asyncio.Lock()

    async def publish_signals(self, signals: list[ViolationSignal], org_id: str) -> bool:
        """Publish a batch of signals after setting the publishing org id.

        Args:
            signals: Signals to publish on behalf of the local organization.
            org_id: Organization identifier to stamp onto the published batch.

        Returns:
            bool: ``True`` when publication succeeded, otherwise ``False`` if
            the channel is disabled.

        Raises:
            None.
        """

        if not self.enabled:
            return False

        published_batch = [
            ViolationSignal(
                category=signal.category,
                severity=signal.severity,
                frequency_bucket=signal.frequency_bucket,
                temporal_trend=signal.temporal_trend,
                org_id=org_id,
                window_start=signal.window_start,
                window_end=signal.window_end,
            )
            for signal in signals
        ]
        async with self._lock:
            self._published.append(published_batch)
        return True

    async def receive_signals(self) -> list[ViolationSignal]:
        """Receive the next queued signal batch.

        Args:
            None.

        Returns:
            list[ViolationSignal]: The oldest queued batch, or an empty list
            when no batches are waiting.

        Raises:
            None.
        """

        async with self._lock:
            if not self._received:
                return []
            return list(self._received.pop(0))

    async def inject_signals(self, signals: list[ViolationSignal]) -> None:
        """Inject a signal batch for tests or loopback scenarios.

        Args:
            signals: Signals to enqueue on the inbound side of the channel.

        Returns:
            None.

        Raises:
            None.
        """

        injected_batch = [
            ViolationSignal(
                category=signal.category,
                severity=signal.severity,
                frequency_bucket=signal.frequency_bucket,
                temporal_trend=signal.temporal_trend,
                org_id=signal.org_id,
                window_start=signal.window_start,
                window_end=signal.window_end,
            )
            for signal in signals
        ]
        async with self._lock:
            self._received.append(injected_batch)


@dataclass(frozen=True, slots=True)
class AmendmentSuggestion:
    """Federated recommendation for constitutional rule coverage changes.

    Use this dataclass to communicate a bounded policy-learning outcome back to
    local governance operators. Suggestions summarize the category, desired
    severity, reasoning, and capped confidence derived from peer cohorts.

    Invariants:
        ``confidence`` is bounded by the configured peer influence cap.
        ``source_org_count`` counts unique contributing peers only.
        Suggestions never include raw peer evidence or matched content.
    """

    category: str
    suggested_severity: str
    reason: str
    confidence: float
    source_org_count: int


def generate_amendment_suggestions(
    local_vector: GovernanceCapabilityVector,
    peer_signals: list[ViolationSignal],
    max_peer_influence: float = 0.1,
) -> list[AmendmentSuggestion]:
    """Generate capped constitutional amendment suggestions from peer signals.

    Args:
        local_vector: Local organization's current capability coverage.
        peer_signals: Privacy-preserving peer observations to analyze.
        max_peer_influence: Upper bound on confidence contributed by peer data.

    Returns:
        list[AmendmentSuggestion]: Suggested local coverage changes ordered by
        descending confidence.

    Raises:
        None.
    """

    qualifying: dict[str, _SignalAggregate] = {}
    for signal in peer_signals:
        if signal.frequency_bucket != "high":
            continue
        severity = signal.severity.strip().upper()
        if SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER["HIGH"]:
            continue

        category = signal.category.strip().lower()
        existing = qualifying.get(category)
        if existing is None:
            qualifying[category] = _SignalAggregate(
                severity=severity,
                org_ids={signal.org_id} if signal.org_id else set(),
                trends={signal.temporal_trend},
            )
            continue

        if SEVERITY_ORDER[severity] > SEVERITY_ORDER[existing.severity]:
            existing.severity = severity
        if signal.org_id:
            existing.org_ids.add(signal.org_id)
        existing.trends.add(signal.temporal_trend)

    suggestions: list[AmendmentSuggestion] = []
    for category, details in qualifying.items():
        suggested_severity = details.severity
        local_severity = local_vector.category_severities.get(category)
        if (
            local_severity is not None
            and SEVERITY_ORDER[local_severity] >= SEVERITY_ORDER[suggested_severity]
        ):
            continue

        source_org_count = len(details.org_ids)
        base_confidence = 0.05 * max(source_org_count, 1)
        if "increasing" in details.trends:
            base_confidence += 0.01
        # Peer learning is deliberately bounded so federated observations can
        # inform local governance without dominating it.
        confidence = min(base_confidence, max_peer_influence)

        coverage_state = (
            f"current local coverage is {local_severity}"
            if local_severity is not None
            else "category is not covered locally"
        )
        suggestions.append(
            AmendmentSuggestion(
                category=category,
                suggested_severity=suggested_severity,
                reason=(
                    f"Peer federation signals show high-frequency {suggested_severity} "
                    f"violations while {coverage_state}."
                ),
                confidence=confidence,
                source_org_count=source_org_count,
            )
        )

    return sorted(suggestions, key=lambda item: item.confidence, reverse=True)


def _bucket_for_count(count: int) -> str:
    if count <= 0:
        return "none"
    if count < 5:
        return "low"
    if count <= 50:
        return "medium"
    return "high"


def _compute_trend(first_half: int, second_half: int) -> str:
    if second_half > first_half:
        return "increasing"
    if second_half < first_half:
        return "decreasing"
    return "stable"


def _bucket_index(bucket: str) -> int:
    try:
        return FREQUENCY_BUCKETS.index(bucket)
    except ValueError:
        return 0


def _laplace_noise(rng: random.Random, scale: float) -> float:
    if scale <= 0.0:
        return 0.0
    uniform = rng.random() - 0.5
    if uniform == 0.0:
        return 0.0
    return -scale * math.copysign(math.log1p(-2.0 * abs(uniform)), uniform)


def _seed_for_signals(signals: list[ViolationSignal], epsilon: float) -> int:
    seed_material = "|".join(
        [
            f"{signal.category}:{signal.severity}:{signal.frequency_bucket}:"
            f"{signal.temporal_trend}:{signal.org_id}:{signal.window_start}:{signal.window_end}"
            for signal in signals
        ]
        + [f"{epsilon:.6f}"]
    )
    return sum(ord(char) for char in seed_material)


__all__ = [
    "AmendmentSuggestion",
    "PolicyLearningChannel",
    "ViolationSignal",
    "apply_differential_privacy",
    "compute_violation_signals",
    "generate_amendment_suggestions",
]
