"""Core data models for federation discovery, trust, and capability exchange.

The federation package avoids sharing raw constitutional rules across
organizations. Instead, it serializes peer metadata, handshake state, and
privacy-preserving governance summaries into compact dataclasses that can move
through registries, audit logs, and transport layers without losing the
fail-closed semantics expected by the enhanced agent bus.

Key concepts:
    Trust levels model how much confidence the local organization has in a
        remote peer.
    Federation peers hold transport and governance metadata for discovery and
        lifecycle management.
    Handshakes represent bilateral HMAC challenge-response state.
    Governance capability vectors summarize policy coverage without exposing
        rule internals.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from secrets import token_hex
from time import time
from uuid import uuid4


class TrustLevel(Enum):
    """Trust tier assigned to a federation peer.

    Use this enum when persisting or comparing federation trust state across the
    registry, handshake flow, or transport adapters. The ordering is
    intentional: higher numeric values represent strictly more trusted peers.

    Invariants:
        Values are monotonic and safe for integer comparison.
        ``VERIFIED`` is the minimum level treated as trusted for discovery.
    """

    UNTRUSTED = 0
    VERIFIED = 1
    TRUSTED = 2


@dataclass(frozen=True, slots=True)
class FederationPeer:
    """Metadata describing a discoverable federated governance peer.

    Use this dataclass whenever a remote organization must be represented in the
    registry or in transport payloads. It carries the minimum information needed
    to identify the peer, validate its advertised governance state, and route
    federation traffic.

    Invariants:
        ``org_id`` uniquely identifies the peer inside a registry.
        ``capabilities`` is a normalized immutable set of high-level features.
        ``trust_level`` must be a valid :class:`TrustLevel`.
    """

    org_id: str
    constitutional_hash: str
    public_key: str
    capabilities: frozenset[str]
    kafka_topic_prefix: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    last_heartbeat: float = 0.0
    expires_at: float = 0.0

    def to_dict(self) -> dict[str, str | float | int | list[str]]:
        """Serialize the peer to a plain dictionary.

        Args:
            None.

        Returns:
            dict[str, str | float | int | list[str]]: JSON-serializable peer
            metadata suitable for transport or storage.

        Raises:
            None.
        """

        return {
            "org_id": self.org_id,
            "constitutional_hash": self.constitutional_hash,
            "public_key": self.public_key,
            "capabilities": sorted(self.capabilities),
            "kafka_topic_prefix": self.kafka_topic_prefix,
            "trust_level": self.trust_level.value,
            "last_heartbeat": self.last_heartbeat,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FederationPeer:
        """Deserialize a peer from a plain dictionary.

        Args:
            data: Serialized peer metadata produced by :meth:`to_dict` or an
                equivalent transport payload.

        Returns:
            FederationPeer: A normalized immutable peer instance.

        Raises:
            KeyError: If a required peer field is missing.
            ValueError: If ``trust_level`` cannot be coerced into a valid enum
                member.
        """

        raw_trust_level = data.get("trust_level", TrustLevel.UNTRUSTED.value)
        trust_level = _coerce_trust_level(raw_trust_level)
        raw_capabilities = data.get("capabilities", ())
        capabilities = frozenset(str(capability) for capability in raw_capabilities)
        return cls(
            org_id=str(data["org_id"]),
            constitutional_hash=str(data["constitutional_hash"]),
            public_key=str(data["public_key"]),
            capabilities=capabilities,
            kafka_topic_prefix=str(data["kafka_topic_prefix"]),
            trust_level=trust_level,
            last_heartbeat=float(data.get("last_heartbeat", 0.0)),
            expires_at=float(data.get("expires_at", 0.0)),
        )


@dataclass(slots=True)
class FederationHandshake:
    """Challenge-response state for a bilateral federation handshake.

    Use this dataclass to carry challenge material and completion state between
    initiator, responder, and registry code. It intentionally stores only the
    handshake metadata required for HMAC verification, not any long-lived secret
    material.

    Invariants:
        ``handshake_id`` is unique per challenge.
        ``challenge`` is random per handshake and safe to disclose.
        ``response_signature`` remains unset until the responder signs the
        challenge.
    """

    initiator_org_id: str
    responder_org_id: str | None = None
    handshake_id: str = field(default_factory=lambda: str(uuid4()))
    challenge: str = field(default_factory=lambda: token_hex(32))
    response_signature: str | None = None
    status: str = "PENDING"
    created_at: float = field(default_factory=time)


@dataclass(frozen=True, slots=True)
class GovernanceCapabilityVector:
    """Privacy-preserving summary of governance coverage for one organization.

    Use this dataclass when organizations need to compare constitutional
    coverage without exposing raw rule text, keyword lists, or pattern
    matchers. It is the canonical federation representation for merge and
    compatibility checks.

    Invariants:
        ``category_severities`` maps normalized categories to supported
        severities only.
        ``total_rules`` counts active rules that contributed to the vector.
        ``version`` and ``org_id`` are metadata only and do not change
        intersection semantics.
    """

    category_severities: dict[str, str]
    total_rules: int
    version: str
    org_id: str = ""


def _coerce_trust_level(value: object) -> TrustLevel:
    """Coerce a serialized value back into a trust level."""

    if isinstance(value, TrustLevel):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in TrustLevel.__members__:
            return TrustLevel[normalized]
        return TrustLevel(int(value))
    return TrustLevel(int(value))


__all__ = [
    "FederationHandshake",
    "FederationPeer",
    "GovernanceCapabilityVector",
    "TrustLevel",
]
