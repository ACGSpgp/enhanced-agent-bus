"""Shim for src.core.shared.security.pqc."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.shared.security.pqc import (  # noqa: F401
        APPROVED_CLASSICAL,
        APPROVED_PQC,
        CONSTITUTIONAL_HASH,
        HYBRID_MODE_ENABLED,
        ClassicalKeyRejectedError,
        ConstitutionalHashMismatchError,
        KeyRegistryUnavailableError,
        MigrationRequiredError,
        PQCError,
        PQCKeyGenerationError,
        PQCKeyRequiredError,
        PQCSignatureError,
        PQCVerificationError,
        SignatureSubstitutionError,
        UnsupportedAlgorithmError,
        UnsupportedPQCAlgorithmError,
        normalize_to_nist,
    )
else:
    try:
        from src.core.shared.security.pqc import *  # noqa: F403
        # KeyRegistryUnavailableError is not in src.core.__all__; import explicitly.
        try:
            from src.core.shared.security.pqc import KeyRegistryUnavailableError  # noqa: F401
        except ImportError:
            class KeyRegistryUnavailableError(PQCError):  # type: ignore[misc,name-defined]
                pass
    except ImportError:
        CONSTITUTIONAL_HASH = "608508a9bd224290"
        APPROVED_PQC = frozenset({"ML-KEM-768", "ML-DSA-65", "SLH-DSA-SHA2-128s"})
        APPROVED_CLASSICAL = frozenset({"RSA-4096", "ECDSA-P384", "Ed25519"})
        HYBRID_MODE_ENABLED = True

        class PQCError(Exception):
            """Base PQC error for standalone mode."""

        class UnsupportedPQCAlgorithmError(PQCError):
            pass

        class PQCKeyRequiredError(PQCError):
            pass

        class ClassicalKeyRejectedError(PQCError):
            pass

        class MigrationRequiredError(PQCError):
            pass

        class KeyRegistryUnavailableError(PQCError):
            pass

        class UnsupportedAlgorithmError(PQCError):
            pass

        class ConstitutionalHashMismatchError(PQCError):
            pass

        class PQCVerificationError(PQCError):
            pass

        class SignatureSubstitutionError(PQCError):
            pass

        class PQCKeyGenerationError(PQCError):
            pass

        class PQCSignatureError(PQCError):
            pass

        class PQCEncryptionError(PQCError):
            pass

        class PQCDecryptionError(PQCError):
            pass

        class PQCDeprecationWarning(PQCError):
            pass

        def normalize_to_nist(algorithm_name: str) -> str:
            """Standalone normalization shim."""
            upper_name = algorithm_name.upper()
            if upper_name in APPROVED_PQC:
                return upper_name
            raise UnsupportedAlgorithmError(f"Unsupported PQC algorithm: {algorithm_name}")

__all__ = [
    "APPROVED_CLASSICAL",
    "APPROVED_PQC",
    "CONSTITUTIONAL_HASH",
    "HYBRID_MODE_ENABLED",
    "ClassicalKeyRejectedError",
    "ConstitutionalHashMismatchError",
    "KeyRegistryUnavailableError",
    "MigrationRequiredError",
    "PQCError",
    "PQCKeyGenerationError",
    "PQCKeyRequiredError",
    "PQCSignatureError",
    "PQCVerificationError",
    "SignatureSubstitutionError",
    "UnsupportedAlgorithmError",
    "UnsupportedPQCAlgorithmError",
    "normalize_to_nist",
]
