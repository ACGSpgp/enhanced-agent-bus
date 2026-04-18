"""Declarative evolution metrics for flywheel replay and evaluation.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from math import inf, isfinite, nextafter
from statistics import fmean


class InvariantStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_DATA = "insufficient_data"


class EvolutionViolationKind(StrEnum):
    DUPLICATE_EPOCH = "duplicate_epoch"
    MISSING_EPOCH_ONE = "missing_epoch_one"
    GAP = "gap"
    NON_INCREASING = "non_increasing"
    DECELERATION = "deceleration"


@dataclass(frozen=True, slots=True)
class EvolutionRecord:
    """Single metric observation in a flywheel trajectory."""

    metric: str
    epoch: int
    value: float

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ValueError("metric must not be empty")
        if self.epoch < 1:
            raise ValueError("epoch must be >= 1")
        if not isfinite(self.value):
            raise ValueError("value must be finite")


@dataclass(frozen=True, slots=True)
class EvolutionViolation:
    """Concrete invariant break found while assessing a metric history."""

    kind: EvolutionViolationKind
    metric: str
    epoch: int
    detail: str


@dataclass(frozen=True, slots=True)
class EvolutionAssessment:
    """Assessment of a single metric against the declarative evolution contract."""

    metric: str
    epoch_count: int
    starting_value: float | None
    current_value: float | None
    best_value: float | None
    total_gain: float | None
    average_delta: float | None
    deltas: tuple[float, ...]
    accelerations: tuple[float, ...]
    unique_epochs: bool
    contiguous_history: bool
    strictly_increasing: InvariantStatus
    strictly_accelerating: InvariantStatus
    valid: bool
    admissible_next_value: float | None
    violations: tuple[EvolutionViolation, ...]

    def to_summary_metrics(self) -> dict[str, int | float | str | bool | None]:
        return {
            "epoch_count": self.epoch_count,
            "starting_value": self.starting_value,
            "current_value": self.current_value,
            "best_value": self.best_value,
            "total_gain": self.total_gain,
            "average_delta": self.average_delta,
            "strictly_increasing": self.strictly_increasing.value,
            "strictly_accelerating": self.strictly_accelerating.value,
            "unique_epochs": self.unique_epochs,
            "contiguous_history": self.contiguous_history,
            "valid": self.valid,
            "admissible_next_value": self.admissible_next_value,
            "violation_count": len(self.violations),
        }


@dataclass(frozen=True, slots=True)
class EvolutionSummary:
    """Aggregate summary for multiple metric histories."""

    assessments: tuple[EvolutionAssessment, ...]

    @property
    def total_metrics(self) -> int:
        return len(self.assessments)

    @property
    def valid_metrics(self) -> int:
        return sum(1 for item in self.assessments if item.valid)

    @property
    def strictly_increasing_metrics(self) -> int:
        return sum(
            1 for item in self.assessments if item.strictly_increasing is InvariantStatus.PASS
        )

    @property
    def strictly_accelerating_metrics(self) -> int:
        return sum(
            1 for item in self.assessments if item.strictly_accelerating is InvariantStatus.PASS
        )

    @property
    def regression_count(self) -> int:
        return self._count_violation(EvolutionViolationKind.NON_INCREASING)

    @property
    def deceleration_count(self) -> int:
        return self._count_violation(EvolutionViolationKind.DECELERATION)

    @property
    def gap_count(self) -> int:
        return self._count_violation(
            EvolutionViolationKind.MISSING_EPOCH_ONE
        ) + self._count_violation(EvolutionViolationKind.GAP)

    @property
    def duplicate_count(self) -> int:
        return self._count_violation(EvolutionViolationKind.DUPLICATE_EPOCH)

    @property
    def insufficient_increasing_count(self) -> int:
        return sum(
            1
            for item in self.assessments
            if item.strictly_increasing is InvariantStatus.INSUFFICIENT_DATA
        )

    @property
    def insufficient_acceleration_count(self) -> int:
        return sum(
            1
            for item in self.assessments
            if item.strictly_accelerating is InvariantStatus.INSUFFICIENT_DATA
        )

    def to_summary_metrics(self) -> dict[str, int]:
        return {
            "total_metrics": self.total_metrics,
            "valid_metrics": self.valid_metrics,
            "strictly_increasing_metrics": self.strictly_increasing_metrics,
            "strictly_accelerating_metrics": self.strictly_accelerating_metrics,
            "regression_count": self.regression_count,
            "deceleration_count": self.deceleration_count,
            "gap_count": self.gap_count,
            "duplicate_count": self.duplicate_count,
            "insufficient_increasing_count": self.insufficient_increasing_count,
            "insufficient_acceleration_count": self.insufficient_acceleration_count,
        }

    def _count_violation(self, kind: EvolutionViolationKind) -> int:
        return sum(
            1
            for item in self.assessments
            for violation in item.violations
            if violation.kind is kind
        )


def assess_metric_evolution(records: Sequence[EvolutionRecord]) -> EvolutionAssessment:
    """Assess a single metric history against strict evolution invariants."""

    if not records:
        raise ValueError("at least one record is required")

    metrics = {record.metric for record in records}
    if len(metrics) != 1:
        raise ValueError("assess_metric_evolution expects records for exactly one metric")

    metric = next(iter(metrics))
    ordered = sorted(records, key=lambda item: item.epoch)
    violations: list[EvolutionViolation] = []
    unique_records: list[EvolutionRecord] = []
    seen_epochs: set[int] = set()

    for record in ordered:
        if record.epoch in seen_epochs:
            violations.append(
                EvolutionViolation(
                    kind=EvolutionViolationKind.DUPLICATE_EPOCH,
                    metric=metric,
                    epoch=record.epoch,
                    detail=f"epoch {record.epoch} appears more than once for metric {metric!r}",
                )
            )
            continue
        seen_epochs.add(record.epoch)
        unique_records.append(record)

    contiguous_history = True
    if unique_records and unique_records[0].epoch != 1:
        contiguous_history = False
        violations.append(
            EvolutionViolation(
                kind=EvolutionViolationKind.MISSING_EPOCH_ONE,
                metric=metric,
                epoch=unique_records[0].epoch,
                detail="epoch 1 is required before higher epochs can satisfy the contract",
            )
        )

    deltas: list[float] = []
    delta_epochs: list[int] = []
    previous_record: EvolutionRecord | None = None
    for record in unique_records:
        if previous_record is None:
            previous_record = record
            continue
        if record.epoch != previous_record.epoch + 1:
            contiguous_history = False
            violations.append(
                EvolutionViolation(
                    kind=EvolutionViolationKind.GAP,
                    metric=metric,
                    epoch=record.epoch,
                    detail=(
                        f"epoch {record.epoch} is missing predecessor {previous_record.epoch + 1}"
                    ),
                )
            )
            previous_record = record
            continue
        delta = record.value - previous_record.value
        deltas.append(delta)
        delta_epochs.append(record.epoch)
        if delta <= 0:
            violations.append(
                EvolutionViolation(
                    kind=EvolutionViolationKind.NON_INCREASING,
                    metric=metric,
                    epoch=record.epoch,
                    detail=(
                        f"value at epoch {record.epoch} must be strictly greater than epoch "
                        f"{previous_record.epoch}"
                    ),
                )
            )
        previous_record = record

    accelerations: list[float] = []
    for index, (previous_delta, current_delta) in enumerate(pairwise(deltas)):
        acceleration = current_delta - previous_delta
        accelerations.append(acceleration)
        epoch = delta_epochs[index + 1]
        if acceleration <= 0:
            violations.append(
                EvolutionViolation(
                    kind=EvolutionViolationKind.DECELERATION,
                    metric=metric,
                    epoch=epoch,
                    detail=f"delta at epoch {epoch} must be strictly greater than the prior delta",
                )
            )

    strictly_increasing = _resolve_increasing_status(unique_records, contiguous_history, violations)
    strictly_accelerating = _resolve_acceleration_status(
        unique_records, contiguous_history, violations
    )
    admissible_next_value = _admissible_next_value(
        unique_records=unique_records,
        contiguous_history=contiguous_history,
        unique_epochs=len(unique_records) == len(records),
        strictly_increasing=strictly_increasing,
        strictly_accelerating=strictly_accelerating,
    )

    starting_value = unique_records[0].value if unique_records else None
    current_value = unique_records[-1].value if unique_records else None
    best_value = max((record.value for record in unique_records), default=None)

    return EvolutionAssessment(
        metric=metric,
        epoch_count=len(unique_records),
        starting_value=starting_value,
        current_value=current_value,
        best_value=best_value,
        total_gain=(
            (current_value - starting_value)
            if starting_value is not None and current_value is not None
            else None
        ),
        average_delta=fmean(deltas) if deltas else None,
        deltas=tuple(deltas),
        accelerations=tuple(accelerations),
        unique_epochs=len(unique_records) == len(records),
        contiguous_history=contiguous_history,
        strictly_increasing=strictly_increasing,
        strictly_accelerating=strictly_accelerating,
        valid=(
            len(unique_records) == len(records)
            and contiguous_history
            and strictly_increasing is InvariantStatus.PASS
            and strictly_accelerating is InvariantStatus.PASS
        ),
        admissible_next_value=admissible_next_value,
        violations=tuple(violations),
    )


def summarize_evolution_records(records: Iterable[EvolutionRecord]) -> EvolutionSummary:
    """Group raw records by metric and summarize the declarative contract state."""

    grouped: dict[str, list[EvolutionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.metric].append(record)
    assessments = tuple(assess_metric_evolution(grouped[metric]) for metric in sorted(grouped))
    return EvolutionSummary(assessments=assessments)


def _resolve_increasing_status(
    unique_records: Sequence[EvolutionRecord],
    contiguous_history: bool,
    violations: Sequence[EvolutionViolation],
) -> InvariantStatus:
    if len(unique_records) < 2:
        return InvariantStatus.INSUFFICIENT_DATA
    if not contiguous_history:
        return InvariantStatus.FAIL
    if any(violation.kind is EvolutionViolationKind.NON_INCREASING for violation in violations):
        return InvariantStatus.FAIL
    return InvariantStatus.PASS


def _resolve_acceleration_status(
    unique_records: Sequence[EvolutionRecord],
    contiguous_history: bool,
    violations: Sequence[EvolutionViolation],
) -> InvariantStatus:
    if len(unique_records) < 3:
        return InvariantStatus.INSUFFICIENT_DATA
    if not contiguous_history:
        return InvariantStatus.FAIL
    if any(violation.kind is EvolutionViolationKind.NON_INCREASING for violation in violations):
        return InvariantStatus.FAIL
    if any(violation.kind is EvolutionViolationKind.DECELERATION for violation in violations):
        return InvariantStatus.FAIL
    return InvariantStatus.PASS


def _admissible_next_value(
    *,
    unique_records: Sequence[EvolutionRecord],
    contiguous_history: bool,
    unique_epochs: bool,
    strictly_increasing: InvariantStatus,
    strictly_accelerating: InvariantStatus,
) -> float | None:
    if not unique_records or not contiguous_history or not unique_epochs:
        return None
    if strictly_increasing is InvariantStatus.FAIL or strictly_accelerating is InvariantStatus.FAIL:
        return None
    current_value = unique_records[-1].value
    if len(unique_records) == 1:
        return nextafter(current_value, inf)
    last_delta = unique_records[-1].value - unique_records[-2].value
    return nextafter(current_value + last_delta, inf)


__all__ = [
    "EvolutionAssessment",
    "EvolutionRecord",
    "EvolutionSummary",
    "EvolutionViolation",
    "EvolutionViolationKind",
    "InvariantStatus",
    "assess_metric_evolution",
    "summarize_evolution_records",
]
