"""
TEE-style receipt attestation providers for governance receipts.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Protocol, TypeAlias

try:
    from enhanced_agent_bus._compat.types import JSONDict
except ImportError:
    JSONDict: TypeAlias = dict[str, Any]


class ReceiptAttestationProvider(Protocol):
    def attest(self, payload: JSONDict) -> JSONDict | None: ...


@dataclass(slots=True)
class LocalTeeAttestationProvider:
    provider_name: str = "local-tee"
    mode: str = "local"

    def attest(self, payload: JSONDict) -> JSONDict:
        measurement = hashlib.sha256(repr(sorted(payload.items())).encode()).hexdigest()
        return {
            "provider": self.provider_name,
            "mode": self.mode,
            "measurement": measurement,
            "attested_at": time.time(),
        }


@dataclass(slots=True)
class SgxQuoteAttestationProvider:
    quote: str
    provider_name: str = "sgx"
    mode: str = "sgx"

    def attest(self, payload: JSONDict) -> JSONDict:
        measurement = hashlib.sha256(repr(sorted(payload.items())).encode()).hexdigest()
        return {
            "provider": self.provider_name,
            "mode": self.mode,
            "measurement": measurement,
            "quote": self.quote,
            "attested_at": time.time(),
        }


__all__ = [
    "LocalTeeAttestationProvider",
    "ReceiptAttestationProvider",
    "SgxQuoteAttestationProvider",
]
