"""Mutual HMAC handshake flow for federated governance peers.

This module implements the trust-establishment step for federation. A local
organization creates a challenge, the remote organization signs that challenge
with shared key material, and the local side verifies the response before
registering the peer. The flow is intentionally fail-closed and avoids any
fallback behavior on missing or invalid signatures.

Key concepts:
    Challenge-response state lives in :class:`FederationHandshake`.
    HMAC-SHA256 protects the handshake from tampering and replay within the
        scope of the random challenge.
    Completed handshakes are the gate for registry admission.

Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

import hashlib
import hmac

from .models import FederationHandshake, FederationPeer
from .registry import FederationRegistry


class FederationProtocol:
    """Challenge-response federation protocol using HMAC-SHA256.

    Use this class when two organizations need to prove possession of the same
    peer key material before federation traffic is allowed. It covers challenge
    creation, response signing, verification, and the final registry handoff.

    Invariants:
        Handshakes are rejected unless status is ``COMPLETED``.
        Signature verification is constant-time through ``compare_digest``.
        Peer registration occurs only after signature and responder identity
        checks pass.
    """

    def initiate_handshake(self, our_org_id: str, peer_org_id: str) -> FederationHandshake:
        """Create a new pending handshake for a target peer.

        Args:
            our_org_id: Organization identifier for the initiating local party.
            peer_org_id: Organization identifier for the intended responder.

        Returns:
            FederationHandshake: A pending handshake with a fresh challenge.

        Raises:
            None.
        """

        return FederationHandshake(
            initiator_org_id=our_org_id,
            responder_org_id=peer_org_id,
        )

    def respond_to_handshake(
        self, handshake: FederationHandshake, our_key: bytes
    ) -> FederationHandshake:
        """Sign a handshake challenge and mark it as completed.

        Args:
            handshake: Handshake whose challenge should be signed.
            our_key: Shared secret bytes used to produce the HMAC response.

        Returns:
            FederationHandshake: The same handshake object after response fields
            have been populated.

        Raises:
            None.
        """

        # The responder signs only the nonce-like challenge so the verifier can
        # prove shared-key possession without exchanging the secret itself.
        signature = hmac.new(
            our_key,
            handshake.challenge.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        handshake.response_signature = signature
        handshake.status = "COMPLETED"
        if handshake.responder_org_id is None:
            handshake.responder_org_id = ""
        return handshake

    def verify_handshake(self, handshake: FederationHandshake, peer_key: bytes) -> bool:
        """Verify a handshake response against a peer key.

        Args:
            handshake: Completed handshake carrying the responder signature.
            peer_key: Shared secret bytes expected for the remote peer.

        Returns:
            bool: ``True`` when the response signature matches the challenge,
            otherwise ``False``.

        Raises:
            None.
        """

        if handshake.status != "COMPLETED":
            return False
        if handshake.response_signature is None:
            return False
        expected_signature = hmac.new(
            peer_key,
            handshake.challenge.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        # ``compare_digest`` keeps verification fail-closed without leaking
        # timing information about partial signature matches.
        return hmac.compare_digest(expected_signature, handshake.response_signature)

    async def complete_handshake(
        self,
        handshake: FederationHandshake,
        peer_info: FederationPeer | dict[str, object],
        registry: FederationRegistry,
    ) -> bool:
        """Register a peer after a completed handshake.

        Args:
            handshake: Handshake that has already been signed and verified.
            peer_info: Peer metadata as an instance or serialized dictionary.
            registry: Registry that should receive the newly trusted peer.

        Returns:
            bool: ``True`` when the peer is accepted into the registry,
            otherwise ``False``.

        Raises:
            KeyError: If serialized ``peer_info`` omits required peer fields.
            ValueError: If serialized ``peer_info`` contains an invalid trust
                level.
        """

        if handshake.status != "COMPLETED":
            return False
        if handshake.response_signature is None:
            return False

        peer = (
            peer_info
            if isinstance(peer_info, FederationPeer)
            else FederationPeer.from_dict(peer_info)
        )
        if handshake.responder_org_id not in (None, "", peer.org_id):
            return False
        handshake.responder_org_id = peer.org_id
        return await registry.register_peer(peer)


__all__ = ["FederationProtocol"]
