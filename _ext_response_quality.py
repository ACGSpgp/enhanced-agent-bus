"""
ACGS-2 Enhanced Agent Bus - Response Quality Extension Exports
Constitutional Hash: 608508a9bd224290

Loads the flat ``response_quality.py`` compatibility module and re-exports its
public surface. This avoids importing the sibling ``response_quality/`` package
whose ``__init__`` intentionally exposes a smaller set of names.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_MODULE_PATH = Path(__file__).with_name("response_quality.py")
_SPEC = importlib.util.spec_from_file_location(
    "enhanced_agent_bus._flat_response_quality",
    _MODULE_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    _RQ: Any = None
else:
    _RQ = importlib.util.module_from_spec(_SPEC)
    sys.modules.setdefault("enhanced_agent_bus._flat_response_quality", _RQ)
    _SPEC.loader.exec_module(_RQ)


def _export(name: str, default: Any = object) -> Any:
    if _RQ is None:
        return default
    return getattr(_RQ, name, default)


RESPONSE_QUALITY_AVAILABLE = bool(_export("RESPONSE_QUALITY_AVAILABLE", False))

ValidationStage = _export("ValidationStage")
ResponseValidationResult = _export("ValidationResult")
PipelineStageConfig = _export("PipelineStageConfig")
PipelineConfig = _export("PipelineConfig")
PipelineRunResult = _export("PipelineRunResult")
SyntaxValidator = _export("SyntaxValidator")
SemanticValidator = _export("SemanticValidator")
ConstitutionalValidator = _export("ConstitutionalValidator")
ResponseValidationPipeline = _export("ResponseValidationPipeline")
create_validation_pipeline = _export("create_validation_pipeline", None)

QualityDimension = _export("QualityDimension")
QualityScore = _export("QualityScore")
ScorerThresholds = _export("ScorerThresholds")
CoherenceScorer = _export("CoherenceScorer")
CompletenessScorer = _export("CompletenessScorer")
AlignmentScorer = _export("AlignmentScorer")
QualityScorer = _export("QualityScorer")
create_quality_scorer = _export("create_quality_scorer", None)

RefinementConfig = _export("RefinementConfig")
RefinementStep = _export("RefinementStep")
RefinementResult = _export("RefinementResult")
ResponseRefinementCallback = _export("RefinementCallback")
ResponseRefiner = _export("ResponseRefiner")
create_response_refiner = _export("create_response_refiner", None)

__all__ = [
    "RESPONSE_QUALITY_AVAILABLE",
    "AlignmentScorer",
    "CoherenceScorer",
    "CompletenessScorer",
    "ConstitutionalValidator",
    "PipelineConfig",
    "PipelineRunResult",
    "PipelineStageConfig",
    "QualityDimension",
    "QualityScore",
    "QualityScorer",
    "RefinementConfig",
    "RefinementResult",
    "RefinementStep",
    "ResponseRefinementCallback",
    "ResponseRefiner",
    "ResponseValidationPipeline",
    "ResponseValidationResult",
    "ScorerThresholds",
    "SemanticValidator",
    "SyntaxValidator",
    "ValidationStage",
    "create_quality_scorer",
    "create_response_refiner",
    "create_validation_pipeline",
]

_EXT_ALL = __all__
