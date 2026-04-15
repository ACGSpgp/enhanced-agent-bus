"""
Signing provider abstractions for bundle and audit signing.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import os
import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Protocol, TypeAlias

from cryptography.hazmat.primitives.asymmetric import ed25519

try:
    from enhanced_agent_bus._compat.types import JSONDict
except ImportError:
    JSONDict: TypeAlias = dict[str, Any]


class SigningProvider(Protocol):
    key_id: str
    algorithm: str
    provider_name: str

    def sign(self, payload: bytes) -> bytes: ...

    def metadata(self) -> JSONDict: ...


@dataclass(slots=True)
class LocalEd25519SigningProvider:
    private_key_hex: str
    key_id: str = "local-ed25519"
    provider_name: str = "local"
    algorithm: str = "ed25519"

    def sign(self, payload: bytes) -> bytes:
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(self.private_key_hex))
        return private_key.sign(payload)

    def metadata(self) -> JSONDict:
        return {
            "provider": self.provider_name,
            "algorithm": self.algorithm,
            "key_id": self.key_id,
        }


@dataclass(slots=True)
class HsmSigningProvider:
    secret: bytes
    key_id: str = "hsm-key"
    provider_name: str = "hsm"
    algorithm: str = "hmac-sha256"
    module_path: str | None = None
    key_label: str | None = None

    def sign(self, payload: bytes) -> bytes:
        # HSM-ready seam: current implementation uses process-local keyed signing so callers can
        # integrate PKCS#11 / CloudHSM later without changing audit/bundle call sites.
        return hmac.new(self.secret, payload, hashlib.sha256).digest()

    def metadata(self) -> JSONDict:
        return {
            "provider": self.provider_name,
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "module_path": self.module_path,
            "key_label": self.key_label,
        }


def canonical_signing_payload(payload: JSONDict) -> bytes:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def resolve_signing_provider(
    explicit_provider: SigningProvider | None = None,
) -> SigningProvider | None:
    if explicit_provider is not None:
        return explicit_provider

    hsm_secret = os.getenv("ACGS_SIGNING_HSM_SECRET")
    if hsm_secret:
        return HsmSigningProvider(
            secret=hsm_secret.encode(),
            key_id=os.getenv("ACGS_SIGNING_HSM_KEY_ID", "hsm-key"),
            module_path=os.getenv("ACGS_SIGNING_HSM_MODULE"),
            key_label=os.getenv("ACGS_SIGNING_HSM_KEY_LABEL"),
        )

    private_key_hex = os.getenv("ACGS_SIGNING_PRIVATE_KEY_HEX")
    if private_key_hex:
        return LocalEd25519SigningProvider(
            private_key_hex=private_key_hex,
            key_id=os.getenv("ACGS_SIGNING_KEY_ID", "local-ed25519"),
        )

    return None


__all__ = [
    "HsmSigningProvider",
    "LocalEd25519SigningProvider",
    "SigningProvider",
    "canonical_signing_payload",
    "resolve_signing_provider",
]
