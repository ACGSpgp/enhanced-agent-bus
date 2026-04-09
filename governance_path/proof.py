"""Compact proof aggregation for governance paths.

This module converts a full governance path into a transport-friendly proof
header. Each hop signature becomes a Merkle leaf, allowing recipients to keep a
single root in headers while still supporting inclusion proofs for individual
segments when deeper inspection is required.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass

from .models import GovernancePath, PathSegment


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _level_sizes(leaf_count: int) -> list[int]:
    if leaf_count <= 0:
        return []

    sizes = [leaf_count]
    current_size = leaf_count
    while current_size > 1:
        current_size = (current_size + 1) // 2
        sizes.append(current_size)
    return sizes


@dataclass(slots=True)
class AggregatedProof:
    """Compact aggregate proof metadata for a governance path.

    Use this structure when the full path is too large to forward inline but a
    downstream system still needs a tamper-evident summary of the traversed
    route.

    Invariants:
        - ``merkle_root`` is derived from the ordered segment signatures.
        - ``segment_count`` must match the leaf count used to build the tree.
        - ``constitutional_hash`` summarizes the path-wide governance context.
    """

    path_id: str
    merkle_root: str
    segment_count: int
    constitutional_hash: str
    timestamp: float

    def to_dict(self) -> dict[str, str | int | float]:
        """Serialize the proof to a JSON-safe dictionary.

        Returns:
            A dictionary suitable for JSON encoding and header transport.
        """
        return {
            "path_id": self.path_id,
            "merkle_root": self.merkle_root,
            "segment_count": self.segment_count,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AggregatedProof:
        """Deserialize aggregate proof metadata from a dictionary.

        Args:
            data: Serialized proof payload.

        Returns:
            An ``AggregatedProof`` instance reconstructed from the dictionary.

        Raises:
            KeyError: If required proof fields are missing.
            ValueError: If numeric fields cannot be coerced to the expected
                types.
        """
        return cls(
            path_id=str(data["path_id"]),
            merkle_root=str(data["merkle_root"]),
            segment_count=int(data["segment_count"]),
            constitutional_hash=str(data["constitutional_hash"]),
            timestamp=float(data["timestamp"]),
        )


def build_merkle_tree(segments: list[PathSegment]) -> list[str]:
    """Build a flat Merkle tree with leaves first and the root last.

    Args:
        segments: Ordered governance path segments whose signatures become the
            Merkle leaves.

    Returns:
        A flat list containing every tree level in sequence, with leaves first
        and the root hash last.
    """
    if not segments:
        return []

    current_level = [_hash_text(segment.signature) for segment in segments]
    tree = list(current_level)

    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            # Duplicate the last node on odd-width levels so every parent hash
            # is computed from exactly two children.
            current_level = [*current_level, current_level[-1]]

        next_level = []
        for index in range(0, len(current_level), 2):
            parent_hash = _hash_text(current_level[index] + current_level[index + 1])
            next_level.append(parent_hash)
        tree.extend(next_level)
        current_level = next_level

    return tree


def aggregate_proof(path: GovernancePath) -> AggregatedProof:
    """Aggregate a governance path into Merkle-root proof metadata.

    Args:
        path: Governance path to summarize.

    Returns:
        Aggregate proof metadata that can be serialized into a compact header.

    Raises:
        ValueError: If the supplied path has no segments.
    """
    tree = build_merkle_tree(path.segments)
    if not tree:
        raise ValueError("Cannot aggregate proof for an empty governance path")

    return AggregatedProof(
        path_id=path.path_id,
        merkle_root=tree[-1],
        segment_count=len(path.segments),
        constitutional_hash=path.segments[0].constitutional_hash,
        timestamp=time.time(),
    )


def inclusion_proof(tree: list[str], leaf_index: int, leaf_count: int) -> list[tuple[str, str]]:
    """Build the sibling path needed to verify one leaf against the Merkle root.

    Args:
        tree: Flat Merkle tree as returned by :func:`build_merkle_tree`.
        leaf_index: Zero-based index of the leaf to prove.
        leaf_count: Number of original leaves used to build the tree.

    Returns:
        A list of ``(sibling_hash, side)`` tuples that reconstruct the root.

    Raises:
        ValueError: If the tree shape does not match ``leaf_count`` or
            ``leaf_count`` is not positive.
        IndexError: If ``leaf_index`` is outside the leaf range.
    """
    if leaf_count <= 0:
        raise ValueError("leaf_count must be positive")
    if leaf_index < 0 or leaf_index >= leaf_count:
        raise IndexError("leaf_index out of range")

    level_sizes = _level_sizes(leaf_count)
    if sum(level_sizes) != len(tree):
        raise ValueError("tree shape does not match leaf_count")

    offsets: list[int] = []
    total = 0
    for size in level_sizes:
        offsets.append(total)
        total += size

    proof_pairs: list[tuple[str, str]] = []
    current_index = leaf_index

    for level, size in enumerate(level_sizes[:-1]):
        level_offset = offsets[level]
        # Offsets map the logical tree level back into the flat storage layout
        # returned by build_merkle_tree().
        if current_index % 2 == 0:
            sibling_index = current_index + 1 if current_index + 1 < size else current_index
            sibling_side = "right"
        else:
            sibling_index = current_index - 1
            sibling_side = "left"

        proof_pairs.append((tree[level_offset + sibling_index], sibling_side))
        current_index //= 2

    return proof_pairs


def verify_inclusion(
    leaf_hash: str,
    proof_pairs: list[tuple[str, str]],
    expected_root: str,
) -> bool:
    """Verify a Merkle inclusion proof against the expected root.

    Args:
        leaf_hash: Hash of the leaf being proven.
        proof_pairs: Sibling path returned by :func:`inclusion_proof`.
        expected_root: Merkle root that the proof should reconstruct.

    Returns:
        ``True`` when the proof reconstructs ``expected_root``, otherwise
        ``False``.

    Raises:
        ValueError: If a proof tuple contains an unsupported side marker.
    """
    current_hash = leaf_hash
    for sibling_hash, side in proof_pairs:
        if side == "left":
            current_hash = _hash_text(sibling_hash + current_hash)
            continue
        if side == "right":
            current_hash = _hash_text(current_hash + sibling_hash)
            continue
        raise ValueError(f"Unsupported proof side: {side}")
    return current_hash == expected_root


def encode_proof_header(proof: AggregatedProof) -> str:
    """Encode aggregate proof metadata into a URL-safe header string.

    Args:
        proof: Aggregate proof metadata to encode.

    Returns:
        A URL-safe base64-encoded JSON payload suitable for transport headers.
    """
    payload = json.dumps(proof.to_dict()).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decode_proof_header(header: str) -> AggregatedProof:
    """Decode a URL-safe aggregate proof header.

    Args:
        header: URL-safe base64-encoded proof payload.

    Returns:
        The decoded ``AggregatedProof`` instance.

    Raises:
        binascii.Error: If the header is not valid base64.
        json.JSONDecodeError: If the decoded payload is not valid JSON.
        KeyError: If required proof fields are missing.
        ValueError: If proof fields cannot be coerced to the expected types.
    """
    payload = base64.urlsafe_b64decode(header.encode("utf-8")).decode("utf-8")
    return AggregatedProof.from_dict(json.loads(payload))
