"""
Optional Chaos Engineering Framework (T003).
Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .chaos import (
        CONSTITUTIONAL_HASH as CHAOS_CONSTITUTIONAL_HASH,
    )
    from .chaos import (
        ChaosExperiment,
        CPUStressScenario,
        DependencyFailureScenario,
        ExperimentPhase,
        ExperimentResult,
        ExperimentStatus,
        InMemoryMetricCollector,
        LatencyInjectionScenario,
        MemoryPressureScenario,
        NetworkPartitionScenario,
        ScenarioExecutor,
        ScenarioStatus,
        SteadyStateHypothesis,
        SteadyStateValidator,
        ValidationMetric,
        chaos_experiment,
        get_experiment_registry,
        reset_experiment_registry,
    )
    from .chaos import (
        ValidationResult as ChaosValidationResult,
    )
else:
    try:
        from .chaos import CONSTITUTIONAL_HASH as CHAOS_CONSTITUTIONAL_HASH  # noqa: F401
        from .chaos import (
            ChaosExperiment,
            CPUStressScenario,
            DependencyFailureScenario,
            ExperimentPhase,
            ExperimentResult,
            ExperimentStatus,
            InMemoryMetricCollector,
            LatencyInjectionScenario,
            MemoryPressureScenario,
            NetworkPartitionScenario,
            ScenarioExecutor,
            ScenarioStatus,
            SteadyStateHypothesis,
            SteadyStateValidator,
            ValidationMetric,
            chaos_experiment,
            get_experiment_registry,
            reset_experiment_registry,
        )
        from .chaos import ValidationResult as ChaosValidationResult

        CHAOS_ENGINEERING_AVAILABLE = True
    except ImportError:
        CHAOS_ENGINEERING_AVAILABLE = False
        ChaosExperiment: Any = object
        CPUStressScenario: Any = object
        DependencyFailureScenario: Any = object
        ExperimentPhase: Any = object
        ExperimentResult: Any = object
        ExperimentStatus: Any = object
        LatencyInjectionScenario: Any = object
        MemoryPressureScenario: Any = object
        InMemoryMetricCollector: Any = object
        NetworkPartitionScenario: Any = object
        ScenarioExecutor: Any = object
        ScenarioStatus: Any = object
        SteadyStateHypothesis: Any = object
        SteadyStateValidator: Any = object
        ValidationMetric: Any = object
        ChaosValidationResult: Any = object
        chaos_experiment: Any = object
        get_experiment_registry: Any = object
        reset_experiment_registry: Any = object

_EXT_ALL = [
    "CHAOS_ENGINEERING_AVAILABLE",
    "CHAOS_CONSTITUTIONAL_HASH",
    "ChaosExperiment",
    "CPUStressScenario",
    "DependencyFailureScenario",
    "ExperimentPhase",
    "ExperimentResult",
    "ExperimentStatus",
    "LatencyInjectionScenario",
    "MemoryPressureScenario",
    "InMemoryMetricCollector",
    "NetworkPartitionScenario",
    "ScenarioExecutor",
    "ScenarioStatus",
    "SteadyStateHypothesis",
    "SteadyStateValidator",
    "ValidationMetric",
    "ChaosValidationResult",
    "chaos_experiment",
    "get_experiment_registry",
    "reset_experiment_registry",
]
