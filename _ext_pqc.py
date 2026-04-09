# Constitutional Hash: 608508a9bd224290
"""Optional Post-Quantum Cryptography validators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pqc_validators import (
        PQCConfig,
        PQCMetadata,
        validate_constitutional_hash_pqc,
        validate_maci_record_pqc,
    )
else:
    try:
        from .pqc_validators import (
            PQCConfig,
            PQCMetadata,
            validate_constitutional_hash_pqc,
            validate_maci_record_pqc,
        )

        PQC_VALIDATORS_AVAILABLE = True
    except ImportError:
        PQC_VALIDATORS_AVAILABLE = False
        validate_constitutional_hash_pqc: Any = object
        validate_maci_record_pqc: Any = object
        PQCConfig: Any = object
        PQCMetadata: Any = object

_EXT_ALL = [
    "PQC_VALIDATORS_AVAILABLE",
    "validate_constitutional_hash_pqc",
    "validate_maci_record_pqc",
    "PQCConfig",
    "PQCMetadata",
]
