"""Validator surface for message_processor (Cat 5 split).

Thin re-export module: concentrates validation-related helpers
(``_perform_security_scan``, ``_requires_independent_validation``,
``_enforce_independent_validator_gate``, ``_enforce_autonomy_tier``) that
live on :class:`MessageProcessor` in the implementation module, plus the
shared :class:`ValidationResult` type. No behavior change.
"""

from __future__ import annotations

from ..validators import ValidationResult
from . import MessageProcessor

__all__ = ["MessageProcessor", "ValidationResult"]
