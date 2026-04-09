"""Core data structures for SCION-style governance-path routing.

This module defines the hop-level and path-level objects used to capture an
authenticated processing topology. A :class:`PathSegment` represents one
validator hop and carries the checkpoint evidence for that hop, while a
:class:`GovernancePath` stores the ordered series of segments and exposes chain
and ordering validation helpers.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise
from time import time
from typing import Any
from uuid import uuid4

CONSTITUTIONAL_HASH = "608508a9bd224290"


class CheckpointType(StrEnum):
    """Canonical governance checkpoints that can appear along a routing path.

    Use this enum when serializing or validating the governance operations
    attached to a hop. The values are stable wire-format strings, and parsers in
    this package accept either enum names or values for compatibility with older
    or externally-produced payloads.
    """

    CONSTITUTIONAL_HASH = "constitutional_hash"
    FULL_VALIDATION = "full_validation"
    MACI_ROLE_CHECK = "maci_role_check"
    IMPACT_SCORING = "impact_scoring"
    HUMAN_REVIEW = "human_review"

    @classmethod
    def parse(cls, raw: str) -> CheckpointType | None:
        """Parse a checkpoint enum member from a raw string.

        Args:
            raw: Serialized checkpoint name or value.

        Returns:
            The matching checkpoint type, or ``None`` when the value is unknown.
        """
        normalized = raw.strip().lower()
        for member in cls:
            if normalized in {member.name.lower(), member.value.lower()}:
                return member
        return None


@dataclass(slots=True)
class PathSegment:
    """One signed hop in a governance path.

    Each segment captures a single validator or router decision point. Use this
    class when a node needs to append its identity, constitutional hash, and
    completed checkpoints to the path before forwarding the message.

    Invariants:
        - ``signature`` authenticates the canonicalized segment fields.
        - ``prev_signature`` binds this hop to the immediately preceding hop.
        - ``checks_performed`` stores wire-format checkpoint strings.
    """

    hop_id: str = field(default_factory=lambda: str(uuid4()))
    node_id: str = ""
    node_role: str = ""
    constitutional_hash: str = CONSTITUTIONAL_HASH
    checks_performed: frozenset[str] = field(default_factory=frozenset)
    timestamp: float = field(default_factory=time)
    signature: str = ""
    prev_signature: str = ""

    def _canonical_payload(self, prev_sig: str) -> str:
        checks = ",".join(sorted(self.checks_performed))
        return f"{self.hop_id}|{self.node_id}|{self.constitutional_hash}|{checks}|{prev_sig}"

    def sign(self, key: bytes, prev_sig: str) -> str:
        """Sign this hop against the previous hop signature.

        Args:
            key: Shared HMAC key used to authenticate the segment.
            prev_sig: Signature from the previous hop, or an empty string for
                the first segment in the path.

        Returns:
            The computed hex-encoded HMAC-SHA256 signature.
        """
        self.prev_signature = prev_sig
        # The previous signature is part of the payload so each hop commits to
        # the full history before it, not only to its local fields.
        payload = self._canonical_payload(prev_sig).encode("utf-8")
        self.signature = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return self.signature

    def verify(self, key: bytes, prev_sig: str) -> bool:
        """Verify this hop against an expected chain state.

        Args:
            key: Shared HMAC key used to recompute the expected signature.
            prev_sig: Signature that should precede this segment in the chain.

        Returns:
            ``True`` when the signature matches the canonical payload for the
            supplied previous signature, otherwise ``False``.
        """
        payload = self._canonical_payload(prev_sig).encode("utf-8")
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the hop to a JSON-safe dictionary.

        Returns:
            A dictionary suitable for JSON encoding and transport.
        """
        return {
            "hop_id": self.hop_id,
            "node_id": self.node_id,
            "node_role": self.node_role,
            "constitutional_hash": self.constitutional_hash,
            "checks_performed": sorted(self.checks_performed),
            "timestamp": self.timestamp,
            "signature": self.signature,
            "prev_signature": self.prev_signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PathSegment:
        """Deserialize a path segment from a dictionary.

        Args:
            d: Serialized segment payload.

        Returns:
            A ``PathSegment`` instance populated from the dictionary.

        Raises:
            ValueError: Propagated if numeric fields cannot be coerced to the
                expected types.
        """
        return cls(
            hop_id=str(d.get("hop_id") or str(uuid4())),
            node_id=str(d.get("node_id", "")),
            node_role=str(d.get("node_role", "")),
            constitutional_hash=str(d.get("constitutional_hash", CONSTITUTIONAL_HASH)),
            checks_performed=frozenset(str(item) for item in d.get("checks_performed", [])),
            timestamp=float(d.get("timestamp", time())),
            signature=str(d.get("signature", "")),
            prev_signature=str(d.get("prev_signature", "")),
        )


@dataclass(slots=True)
class GovernancePath:
    """An ordered governance path composed of signed hop segments.

    Use this class as the container for the end-to-end governance trail that
    travels with a message. It provides integrity checks that are broader than a
    single segment, such as chain continuity and required checkpoint ordering.

    Invariants:
        - ``segments`` are interpreted in traversal order.
        - Each segment after the first should reference the prior signature.
        - ``required_quorum`` is metadata only; the current package does not
          enforce quorum semantics.
    """

    segments: list[PathSegment] = field(default_factory=list)
    path_id: str = field(default_factory=lambda: str(uuid4()))
    required_quorum: int = 1

    def verify_chain(self, key: bytes) -> bool:
        """Verify the full hop-by-hop signature chain.

        Args:
            key: Shared HMAC key used to verify each segment.

        Returns:
            ``True`` when every segment links to the expected previous
            signature and each HMAC verifies, otherwise ``False``.
        """
        prev_sig = ""
        for index, segment in enumerate(self.segments):
            expected_prev = "" if index == 0 else prev_sig
            if segment.prev_signature != expected_prev:
                return False
            if not segment.verify(key, expected_prev):
                return False
            prev_sig = segment.signature
        return True

    def validate_ordering(self) -> tuple[bool, str | None]:
        """Validate that governance checkpoints appear in the expected order.

        Returns:
            A ``(is_valid, error)`` tuple. ``error`` is ``None`` when the path
            order is valid.
        """
        if not self.segments:
            return True, None

        order = {
            CheckpointType.CONSTITUTIONAL_HASH: 0,
            CheckpointType.MACI_ROLE_CHECK: 1,
            CheckpointType.IMPACT_SCORING: 2,
            CheckpointType.FULL_VALIDATION: 3,
            CheckpointType.HUMAN_REVIEW: 4,
        }
        first_seen: dict[CheckpointType, int] = {}

        for index, segment in enumerate(self.segments):
            for raw_check in segment.checks_performed:
                checkpoint = CheckpointType.parse(raw_check)
                # Ordering is based on the first appearance of each checkpoint
                # so repeated checks later in the path do not change precedence.
                if checkpoint is not None and checkpoint not in first_seen:
                    first_seen[checkpoint] = index

        ordered_checkpoints = [
            checkpoint for checkpoint in sorted(first_seen, key=lambda item: order[item])
        ]
        for left, right in pairwise(ordered_checkpoints):
            if first_seen[left] > first_seen[right]:
                return (
                    False,
                    f"{left.name} must appear before {right.name}",
                )
        return True, None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the governance path to a JSON-safe dictionary.

        Returns:
            A dictionary containing serialized segments and path metadata.
        """
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "path_id": self.path_id,
            "required_quorum": self.required_quorum,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GovernancePath:
        """Deserialize a governance path from a dictionary.

        Args:
            d: Serialized governance path payload.

        Returns:
            A ``GovernancePath`` instance populated from the dictionary.

        Raises:
            ValueError: Propagated if numeric fields cannot be coerced to the
                expected types.
        """
        return cls(
            segments=[PathSegment.from_dict(item) for item in d.get("segments", [])],
            path_id=str(d.get("path_id") or str(uuid4())),
            required_quorum=int(d.get("required_quorum", 1)),
        )
