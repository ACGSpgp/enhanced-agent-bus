"""Async-safe registry for federated peer lifecycle management.

This module owns the in-memory source of truth for discovered federation peers.
It is intentionally small and concurrency-safe so higher-level transports can
register, refresh, expire, and query peers without re-implementing lock
discipline around shared state.

Key concepts:
    Peer registration is idempotent by ``org_id`` and rejects duplicates.
    Trust-aware lookup exposes only peers that meet the minimum federation bar.
    Heartbeats and lease expiration support fail-closed peer discovery.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from time import time

from .models import FederationPeer, TrustLevel


class FederationRegistry:
    """In-memory async-safe registry of federated peers.

    Use this class when a process needs a single mutable view of discovered
    federation peers. It is appropriate for test environments, adapter layers,
    and services that already have an external persistence boundary elsewhere.

    Invariants:
        ``_peers`` is keyed by unique organization id.
        All registry mutations occur under ``_lock``.
        Stale or expired peers are removed rather than marked usable.
    """

    def __init__(self) -> None:
        self._peers: dict[str, FederationPeer] = {}
        self._lock = asyncio.Lock()

    async def register_peer(self, peer: FederationPeer) -> bool:
        """Register a peer if it is not already known.

        Args:
            peer: Peer metadata to store in the registry.

        Returns:
            bool: ``True`` when the peer was inserted, otherwise ``False`` if a
            peer with the same organization id already exists.

        Raises:
            None.
        """

        async with self._lock:
            if peer.org_id in self._peers:
                return False
            self._peers[peer.org_id] = peer
            return True

    async def unregister_peer(self, org_id: str) -> bool:
        """Remove a peer from the registry.

        Args:
            org_id: Organization identifier for the peer to remove.

        Returns:
            bool: ``True`` when a peer was removed, otherwise ``False``.

        Raises:
            None.
        """

        async with self._lock:
            if org_id not in self._peers:
                return False
            del self._peers[org_id]
            return True

    async def get_peer(self, org_id: str) -> FederationPeer | None:
        """Return a single peer by organization id.

        Args:
            org_id: Organization identifier to look up.

        Returns:
            FederationPeer | None: The stored peer when present, otherwise
            ``None``.

        Raises:
            None.
        """

        async with self._lock:
            return self._peers.get(org_id)

    async def get_trusted_peers(self) -> list[FederationPeer]:
        """Return peers that have reached at least verified trust.

        Args:
            None.

        Returns:
            list[FederationPeer]: Peers whose trust level is ``VERIFIED`` or
            higher.

        Raises:
            None.
        """

        async with self._lock:
            return [
                peer
                for peer in self._peers.values()
                if peer.trust_level.value >= TrustLevel.VERIFIED.value
            ]

    async def heartbeat(self, org_id: str) -> bool:
        """Refresh a peer heartbeat timestamp.

        Args:
            org_id: Organization identifier for the peer lease to refresh.

        Returns:
            bool: ``True`` when the heartbeat was updated, otherwise ``False``
            if the peer is unknown.

        Raises:
            None.
        """

        async with self._lock:
            peer = self._peers.get(org_id)
            if peer is None:
                return False
            self._peers[org_id] = replace(peer, last_heartbeat=time())
            return True

    async def expire_stale_peers(self, ttl: float = 90.0) -> list[str]:
        """Remove peers with expired leases or stale heartbeats.

        Args:
            ttl: Maximum age in seconds allowed since the last heartbeat before
                a peer is considered stale.

        Returns:
            list[str]: Organization ids removed from the registry.

        Raises:
            None.
        """

        now = time()
        removed: list[str] = []
        async with self._lock:
            for org_id, peer in list(self._peers.items()):
                heartbeat_age = now - peer.last_heartbeat
                is_stale = heartbeat_age > ttl
                is_expired = peer.expires_at > 0.0 and peer.expires_at <= now
                if is_stale or is_expired:
                    removed.append(org_id)
                    del self._peers[org_id]
        return removed


__all__ = ["FederationRegistry"]
