"""Shim for src.core.shared.constitutional_hash."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.shared.constitutional_hash import *  # noqa: F403
else:
    try:
        from src.core.shared.constitutional_hash import *  # noqa: F403
    except ImportError:
        CANONICAL_HASH = "608508a9bd224290"

        @dataclass(frozen=True)
        class ValidationResult:
            """Minimal standalone validation result."""

            is_valid: bool
            normalized_hash: str | None = None
            matched_version: str | None = None
            reason: str = ""
            algorithm: str | None = None
            is_legacy: bool = True

        def validate_constitutional_hash(
            hash_input: str,
            strict: bool = False,
            allow_legacy: bool = True,
        ) -> ValidationResult:
            """Return a compatibility ValidationResult for standalone mode."""
            is_valid = hash_input == CANONICAL_HASH and (allow_legacy or not strict)
            reason = "" if is_valid else "hash_mismatch"
            return ValidationResult(
                is_valid=is_valid,
                normalized_hash=CANONICAL_HASH if is_valid else None,
                matched_version="v1" if is_valid else None,
                reason=reason,
            )

        def get_constitutional_hash() -> str:
            return CANONICAL_HASH

        def get_active_constitutional_hash() -> str:
            return f"sha256:v1:{CANONICAL_HASH}"

        def get_active_hash_value() -> str:
            return CANONICAL_HASH

        def get_constitutional_hash_versioned() -> str:
            return f"sha256:v1:{CANONICAL_HASH}"

        def normalize_constitutional_hash(hash_input: str) -> str:
            return hash_input if ":" in hash_input else f"sha256:v1:{hash_input}"

        def matches_active_constitutional_hash(hash_input: str) -> bool:
            return hash_input in {CANONICAL_HASH, f"sha256:v1:{CANONICAL_HASH}"}
