# Constitutional Hash: 608508a9bd224290
"""Optional Explanation Service for FR-12 Decision Explanation API."""

from collections.abc import Callable
from typing import Any

_CounterfactualEngine: type[Any]
_ExplanationService: type[Any]
_get_explanation_service: Callable[[], Any]
_reset_explanation_service: Callable[[], None]

try:
    from .explanation_service import (
        CounterfactualEngine as _CounterfactualEngineImport,
    )
    from .explanation_service import (
        ExplanationService as _ExplanationServiceImport,
    )
    from .explanation_service import (
        get_explanation_service as _get_explanation_service_import,
    )
    from .explanation_service import (
        reset_explanation_service as _reset_explanation_service_import,
    )

    EXPLANATION_SERVICE_AVAILABLE = True
    _CounterfactualEngine = _CounterfactualEngineImport
    _ExplanationService = _ExplanationServiceImport
    _get_explanation_service = _get_explanation_service_import
    _reset_explanation_service = _reset_explanation_service_import
except ImportError:
    EXPLANATION_SERVICE_AVAILABLE = False
    _CounterfactualEngine = object
    _ExplanationService = object

    def _get_explanation_service() -> Any:
        raise ImportError("Explanation service is unavailable")

    def _reset_explanation_service() -> None:
        return None


CounterfactualEngine: type[Any] = _CounterfactualEngine
ExplanationService: type[Any] = _ExplanationService
get_explanation_service: Callable[[], Any] = _get_explanation_service
reset_explanation_service: Callable[[], None] = _reset_explanation_service

_EXT_ALL = [
    "EXPLANATION_SERVICE_AVAILABLE",
    "ExplanationService",
    "CounterfactualEngine",
    "get_explanation_service",
    "reset_explanation_service",
]
