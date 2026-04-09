"""Compatibility bridge for shared JWT algorithm normalization."""

from __future__ import annotations

from typing import Callable

try:
    from src.core.shared.security.jwt_algorithms import (  # type: ignore[import-not-found]
        ALLOWED_JWT_ALGORITHMS,
        resolve_jwt_algorithm,
    )
except ImportError:
    ALLOWED_JWT_ALGORITHMS = frozenset(
        {"RS256", "RS384", "RS512", "ES256", "ES384", "EdDSA", "HS256"}
    )
    _JWT_ALGORITHM_CANONICAL_MAP = {
        algorithm.lower(): algorithm for algorithm in ALLOWED_JWT_ALGORITHMS
    }

    def resolve_jwt_algorithm(
        *candidates: str | None,
        error_code: str,
        setting_name: str,
        invalid_message: Callable[[str], str] | None = None,
        default: str = "RS256",
    ) -> str:
        del error_code
        configured = next(
            (candidate.strip() for candidate in candidates if candidate and candidate.strip()),
            "",
        )
        if not configured:
            configured = default

        normalized = _JWT_ALGORITHM_CANONICAL_MAP.get(configured.lower())
        if normalized is None:
            if invalid_message is None:
                allowed = ", ".join(sorted(ALLOWED_JWT_ALGORITHMS))
                message = f"{setting_name} must be one of {allowed}. Got {configured!r}."
            else:
                message = invalid_message(configured)
            raise ValueError(message)
        return normalized


__all__ = ["ALLOWED_JWT_ALGORITHMS", "resolve_jwt_algorithm"]
