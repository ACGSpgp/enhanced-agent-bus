from __future__ import annotations

from math import inf, nan, nextafter

import pytest

from enhanced_agent_bus.data_flywheel.metrics import (
    EvolutionRecord,
    EvolutionViolationKind,
    InvariantStatus,
    assess_metric_evolution,
    summarize_evolution_records,
)


def test_assess_metric_evolution_accepts_strictly_accelerating_history() -> None:
    assessment = assess_metric_evolution(
        [
            EvolutionRecord(metric="capability", epoch=1, value=10.0),
            EvolutionRecord(metric="capability", epoch=2, value=12.0),
            EvolutionRecord(metric="capability", epoch=3, value=16.0),
            EvolutionRecord(metric="capability", epoch=4, value=22.0),
            EvolutionRecord(metric="capability", epoch=5, value=30.0),
        ]
    )

    assert assessment.metric == "capability"
    assert assessment.deltas == (2.0, 4.0, 6.0, 8.0)
    assert assessment.accelerations == (2.0, 2.0, 2.0)
    assert assessment.unique_epochs is True
    assert assessment.contiguous_history is True
    assert assessment.strictly_increasing is InvariantStatus.PASS
    assert assessment.strictly_accelerating is InvariantStatus.PASS
    assert assessment.valid is True
    assert assessment.admissible_next_value == nextafter(38.0, inf)


def test_assess_metric_evolution_detects_regression_and_deceleration() -> None:
    assessment = assess_metric_evolution(
        [
            EvolutionRecord(metric="capability", epoch=1, value=10.0),
            EvolutionRecord(metric="capability", epoch=2, value=15.0),
            EvolutionRecord(metric="capability", epoch=3, value=18.0),
            EvolutionRecord(metric="capability", epoch=4, value=17.0),
        ]
    )

    kinds = {violation.kind for violation in assessment.violations}
    assert EvolutionViolationKind.NON_INCREASING in kinds
    assert EvolutionViolationKind.DECELERATION in kinds
    assert assessment.strictly_increasing is InvariantStatus.FAIL
    assert assessment.strictly_accelerating is InvariantStatus.FAIL
    assert assessment.valid is False
    assert assessment.admissible_next_value is None


def test_assess_metric_evolution_does_not_report_acceleration_after_regression() -> None:
    assessment = assess_metric_evolution(
        [
            EvolutionRecord(metric="reliability", epoch=1, value=10.0),
            EvolutionRecord(metric="reliability", epoch=2, value=9.0),
            EvolutionRecord(metric="reliability", epoch=3, value=11.0),
        ]
    )

    kinds = {violation.kind for violation in assessment.violations}
    assert EvolutionViolationKind.NON_INCREASING in kinds
    assert assessment.strictly_increasing is InvariantStatus.FAIL
    assert assessment.strictly_accelerating is InvariantStatus.FAIL
    assert assessment.valid is False
    assert assessment.admissible_next_value is None


def test_assess_metric_evolution_rejects_gaps_and_duplicate_epochs() -> None:
    assessment = assess_metric_evolution(
        [
            EvolutionRecord(metric="reliability", epoch=2, value=83.0),
            EvolutionRecord(metric="reliability", epoch=2, value=84.0),
            EvolutionRecord(metric="reliability", epoch=4, value=95.0),
        ]
    )

    kinds = {violation.kind for violation in assessment.violations}
    assert EvolutionViolationKind.MISSING_EPOCH_ONE in kinds
    assert EvolutionViolationKind.DUPLICATE_EPOCH in kinds
    assert EvolutionViolationKind.GAP in kinds
    assert assessment.unique_epochs is False
    assert assessment.contiguous_history is False
    assert assessment.strictly_increasing is InvariantStatus.FAIL
    assert assessment.strictly_accelerating is InvariantStatus.INSUFFICIENT_DATA
    assert assessment.admissible_next_value is None


def test_assess_metric_evolution_marks_insufficient_history_explicitly() -> None:
    one_epoch = assess_metric_evolution([EvolutionRecord(metric="latency", epoch=1, value=120.0)])
    two_epochs = assess_metric_evolution(
        [
            EvolutionRecord(metric="latency", epoch=1, value=120.0),
            EvolutionRecord(metric="latency", epoch=2, value=121.0),
        ]
    )

    assert one_epoch.strictly_increasing is InvariantStatus.INSUFFICIENT_DATA
    assert one_epoch.strictly_accelerating is InvariantStatus.INSUFFICIENT_DATA
    assert one_epoch.valid is False
    assert one_epoch.admissible_next_value == nextafter(120.0, inf)
    assert two_epochs.strictly_increasing is InvariantStatus.PASS
    assert two_epochs.strictly_accelerating is InvariantStatus.INSUFFICIENT_DATA
    assert two_epochs.valid is False
    assert two_epochs.admissible_next_value == nextafter(122.0, inf)


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_evolution_record_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="value must be finite"):
        EvolutionRecord(metric="capability", epoch=1, value=value)


def test_summarize_evolution_records_aggregates_contract_metrics() -> None:
    summary = summarize_evolution_records(
        [
            EvolutionRecord(metric="capability", epoch=1, value=10.0),
            EvolutionRecord(metric="capability", epoch=2, value=12.0),
            EvolutionRecord(metric="capability", epoch=3, value=16.0),
            EvolutionRecord(metric="reliability", epoch=1, value=80.0),
            EvolutionRecord(metric="reliability", epoch=2, value=79.0),
            EvolutionRecord(metric="reliability", epoch=3, value=81.0),
            EvolutionRecord(metric="reliability", epoch=4, value=82.0),
            EvolutionRecord(metric="freshness", epoch=1, value=1.0),
        ]
    )

    assert summary.total_metrics == 3
    assert summary.valid_metrics == 1
    assert summary.strictly_increasing_metrics == 1
    assert summary.strictly_accelerating_metrics == 1
    assert summary.regression_count == 1
    assert summary.deceleration_count == 1
    assert summary.insufficient_increasing_count == 1
    assert summary.insufficient_acceleration_count == 1
