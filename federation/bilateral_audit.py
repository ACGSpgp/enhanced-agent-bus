"""Tamper-evident bilateral audit records for federated governance actions.

Cross-organization actions need an accountability trail that both sides can
inspect and, when appropriate, countersign. This module provides the append-only
entry format, a small async-safe in-memory log, and HMAC helpers for producing
and verifying bilateral signatures without embedding raw agent payloads.

Key concepts:
    Bilateral entries capture summarized actions and constitutional hashes only.
    The audit log is append-only and confirmation upgrades entries in place.
    HMAC signatures provide non-repudiation signals for bilateral workflows.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from dataclasses import dataclass, field, replace
from time import time
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BilateralAuditEntry:
    """Counter-signed audit record for a bilateral federation event.

    Use this dataclass to persist the summarized facts of a cross-organization
    operation such as a handshake, capability negotiation, or policy-learning
    exchange. It is designed to preserve accountability without storing raw
    transcripts or matched content.

    Invariants:
        ``entry_id`` uniquely identifies the record.
        ``local_signature`` covers the canonical payload for tamper detection.
        ``peer_signature`` is absent until the peer confirms the record.
    """

    local_org_id: str
    peer_org_id: str
    action_summary: str
    local_constitutional_hash: str
    peer_constitutional_hash: str
    local_signature: str
    peer_signature: str | None = None
    bilateral_status: str = "PENDING"
    timestamp: float = field(default_factory=time)
    entry_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, str | float | None]:
        """Serialize the entry to a plain dictionary.

        Args:
            None.

        Returns:
            dict[str, str | float | None]: JSON-serializable audit entry data.

        Raises:
            None.
        """

        return {
            "entry_id": self.entry_id,
            "local_org_id": self.local_org_id,
            "peer_org_id": self.peer_org_id,
            "action_summary": self.action_summary,
            "local_constitutional_hash": self.local_constitutional_hash,
            "peer_constitutional_hash": self.peer_constitutional_hash,
            "local_signature": self.local_signature,
            "peer_signature": self.peer_signature,
            "bilateral_status": self.bilateral_status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BilateralAuditEntry:
        """Deserialize an entry from a plain dictionary.

        Args:
            data: Serialized entry payload produced by :meth:`to_dict` or an
                equivalent transport envelope.

        Returns:
            BilateralAuditEntry: Reconstructed audit entry instance.

        Raises:
            KeyError: If a required entry field is missing.
            ValueError: If a timestamp field cannot be converted to ``float``.
        """

        return cls(
            entry_id=str(data.get("entry_id", str(uuid4()))),
            local_org_id=str(data["local_org_id"]),
            peer_org_id=str(data["peer_org_id"]),
            action_summary=str(data["action_summary"]),
            local_constitutional_hash=str(data["local_constitutional_hash"]),
            peer_constitutional_hash=str(data["peer_constitutional_hash"]),
            local_signature=str(data["local_signature"]),
            peer_signature=(
                None if data.get("peer_signature") is None else str(data.get("peer_signature"))
            ),
            bilateral_status=str(data.get("bilateral_status", "PENDING")),
            timestamp=float(data.get("timestamp", time())),
        )


class BilateralAuditLog:
    """Async-safe append-only bilateral audit log.

    Use this class when bilateral federation actions need a mutable in-memory
    ledger during a process lifetime. It is suitable for tests, lightweight
    services, and adapters that already have durable storage elsewhere.

    Invariants:
        Entries are appended under ``_lock`` to preserve ordering.
        ``confirm`` only transitions entries from ``PENDING`` to ``CONFIRMED``.
        Failure marking does not persist opaque rejection details.
    """

    def __init__(self) -> None:
        self._entries: list[BilateralAuditEntry] = []
        self._lock = asyncio.Lock()

    async def record(self, entry: BilateralAuditEntry) -> None:
        """Append a bilateral audit entry.

        Args:
            entry: Audit entry to append to the log.

        Returns:
            None.

        Raises:
            None.
        """

        async with self._lock:
            self._entries.append(entry)

    async def get_entries(self, org_id: str | None = None) -> list[BilateralAuditEntry]:
        """Return all entries or those involving a specific organization.

        Args:
            org_id: Optional organization identifier to filter by local or peer
                participation.

        Returns:
            list[BilateralAuditEntry]: Matching audit records in insertion
            order.

        Raises:
            None.
        """

        async with self._lock:
            if org_id is None:
                return list(self._entries)
            return [
                entry
                for entry in self._entries
                if entry.local_org_id == org_id or entry.peer_org_id == org_id
            ]

    async def get_pending(self) -> list[BilateralAuditEntry]:
        """Return entries still awaiting peer confirmation.

        Args:
            None.

        Returns:
            list[BilateralAuditEntry]: Entries whose bilateral status is
            ``PENDING``.

        Raises:
            None.
        """

        async with self._lock:
            return [entry for entry in self._entries if entry.bilateral_status == "PENDING"]

    async def confirm(self, entry_id: str, peer_signature: str) -> bool:
        """Counter-sign a bilateral audit entry.

        Args:
            entry_id: Audit entry identifier to confirm.
            peer_signature: Peer-produced signature over the canonical payload.

        Returns:
            bool: ``True`` when the entry was updated, otherwise ``False``.

        Raises:
            None.
        """

        async with self._lock:
            for index, entry in enumerate(self._entries):
                if entry.entry_id != entry_id:
                    continue
                if entry.bilateral_status != "PENDING":
                    return False
                self._entries[index] = replace(
                    entry,
                    peer_signature=peer_signature,
                    bilateral_status="CONFIRMED",
                )
                return True
        return False

    async def mark_failed(self, entry_id: str, reason: str) -> bool:
        """Mark an entry as failed without persisting failure details.

        Args:
            entry_id: Audit entry identifier to mark as failed.
            reason: Human-readable explanation for the failure. The value is
                intentionally ignored to avoid storing sensitive details.

        Returns:
            bool: ``True`` when the entry was updated, otherwise ``False``.

        Raises:
            None.
        """

        _ = reason
        async with self._lock:
            for index, entry in enumerate(self._entries):
                if entry.entry_id != entry_id:
                    continue
                self._entries[index] = replace(entry, bilateral_status="FAILED")
                return True
        return False


def sign_bilateral_entry(entry: BilateralAuditEntry, key: bytes) -> str:
    """Create an HMAC-SHA256 signature for a bilateral audit entry.

    Args:
        entry: Audit entry whose canonical payload should be signed.
        key: Secret key bytes used to compute the HMAC.

    Returns:
        str: Hex-encoded signature for the entry payload.

    Raises:
        None.
    """

    # Signatures cover the canonical serialized summary only, which keeps the
    # bilateral audit trail tamper-evident without including raw agent data.
    return hmac.new(key, _signature_payload(entry), hashlib.sha256).hexdigest()


def verify_bilateral_signature(entry: BilateralAuditEntry, signature: str, key: bytes) -> bool:
    """Verify a bilateral audit entry signature.

    Args:
        entry: Audit entry whose payload should match the signature.
        signature: Hex-encoded signature presented for verification.
        key: Secret key bytes expected for the signing party.

        Returns:
            bool: ``True`` when the signature matches, otherwise ``False``.

        Raises:
            None.
    """

    expected_signature = sign_bilateral_entry(entry, key)
    return hmac.compare_digest(expected_signature, signature)


def _signature_payload(entry: BilateralAuditEntry) -> bytes:
    payload = "|".join(
        [
            entry.entry_id,
            entry.local_org_id,
            entry.peer_org_id,
            entry.action_summary,
            entry.local_constitutional_hash,
            entry.peer_constitutional_hash,
            repr(float(entry.timestamp)),
        ]
    )
    return payload.encode("utf-8")


__all__ = [
    "BilateralAuditEntry",
    "BilateralAuditLog",
    "sign_bilateral_entry",
    "verify_bilateral_signature",
]
