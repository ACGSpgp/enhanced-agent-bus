"""
Tests for federated governance infrastructure.
Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from enhanced_agent_bus.federation import (
    FederationPeer,
    FederationProtocol,
    FederationRegistry,
    GovernanceCapabilityVector,
    MergeSemantic,
    TrustLevel,
    compute_capability_vector,
    compute_intersection,
)


@dataclass
class RuleStub:
    category: str
    severity: str
    active: bool = True
    rule_text: str = "deny risky content"
    keywords: tuple[str, ...] = ("unsafe",)
    patterns: tuple[str, ...] = ("*",)


@pytest.fixture
def peer() -> FederationPeer:
    return FederationPeer(
        org_id="org-alpha",
        constitutional_hash="608508a9bd224290",
        public_key=bytes.fromhex("11" * 32).hex(),
        capabilities=frozenset({"governance", "audit"}),
        kafka_topic_prefix="alpha.gov",
        trust_level=TrustLevel.VERIFIED,
    )


@pytest.fixture
def trusted_peer() -> FederationPeer:
    return FederationPeer(
        org_id="org-bravo",
        constitutional_hash="608508a9bd224290",
        public_key=bytes.fromhex("22" * 32).hex(),
        capabilities=frozenset({"governance"}),
        kafka_topic_prefix="bravo.gov",
        trust_level=TrustLevel.TRUSTED,
    )


@pytest.fixture
def untrusted_peer() -> FederationPeer:
    return FederationPeer(
        org_id="org-charlie",
        constitutional_hash="608508a9bd224290",
        public_key=bytes.fromhex("33" * 32).hex(),
        capabilities=frozenset({"audit"}),
        kafka_topic_prefix="charlie.gov",
        trust_level=TrustLevel.UNTRUSTED,
    )


@pytest.mark.asyncio
async def test_peer_registration(peer: FederationPeer) -> None:
    registry = FederationRegistry()

    assert await registry.register_peer(peer) is True
    stored = await registry.get_peer(peer.org_id)

    assert stored == peer


@pytest.mark.asyncio
async def test_peer_unregister(peer: FederationPeer) -> None:
    registry = FederationRegistry()
    await registry.register_peer(peer)

    assert await registry.unregister_peer(peer.org_id) is True
    assert await registry.get_peer(peer.org_id) is None


@pytest.mark.asyncio
async def test_heartbeat_updates_timestamp(peer: FederationPeer) -> None:
    registry = FederationRegistry()
    await registry.register_peer(peer)

    assert await registry.heartbeat(peer.org_id) is True
    updated = await registry.get_peer(peer.org_id)

    assert updated is not None
    assert updated.last_heartbeat > peer.last_heartbeat


@pytest.mark.asyncio
async def test_expire_stale_peers(peer: FederationPeer, trusted_peer: FederationPeer) -> None:
    registry = FederationRegistry()
    await registry.register_peer(peer)
    await registry.register_peer(trusted_peer)
    await registry.heartbeat(trusted_peer.org_id)

    removed = await registry.expire_stale_peers(ttl=0.01)

    assert removed == [peer.org_id]
    assert await registry.get_peer(peer.org_id) is None
    remaining = await registry.get_peer(trusted_peer.org_id)

    assert remaining is not None
    assert remaining.org_id == trusted_peer.org_id
    assert remaining.trust_level == trusted_peer.trust_level
    assert remaining.last_heartbeat > trusted_peer.last_heartbeat


@pytest.mark.asyncio
async def test_get_trusted_peers_filters(
    peer: FederationPeer,
    trusted_peer: FederationPeer,
    untrusted_peer: FederationPeer,
) -> None:
    registry = FederationRegistry()
    await registry.register_peer(peer)
    await registry.register_peer(trusted_peer)
    await registry.register_peer(untrusted_peer)

    trusted = await registry.get_trusted_peers()

    assert {item.org_id for item in trusted} == {peer.org_id, trusted_peer.org_id}


@pytest.mark.asyncio
async def test_handshake_full_lifecycle(trusted_peer: FederationPeer) -> None:
    registry = FederationRegistry()
    protocol = FederationProtocol()
    key = bytes.fromhex(trusted_peer.public_key)

    handshake = protocol.initiate_handshake("org-local", trusted_peer.org_id)
    completed = protocol.respond_to_handshake(handshake, key)

    assert completed.status == "COMPLETED"
    assert completed.responder_org_id == trusted_peer.org_id
    assert protocol.verify_handshake(completed, key) is True
    assert await protocol.complete_handshake(completed, trusted_peer, registry) is True
    assert await registry.get_peer(trusted_peer.org_id) == trusted_peer


def test_handshake_bad_signature_rejected(trusted_peer: FederationPeer) -> None:
    protocol = FederationProtocol()
    handshake = protocol.initiate_handshake("org-local", trusted_peer.org_id)
    protocol.respond_to_handshake(handshake, bytes.fromhex(trusted_peer.public_key))

    assert protocol.verify_handshake(handshake, bytes.fromhex("44" * 32)) is False


@pytest.mark.asyncio
async def test_handshake_incomplete_rejected(trusted_peer: FederationPeer) -> None:
    registry = FederationRegistry()
    protocol = FederationProtocol()
    handshake = protocol.initiate_handshake("org-local", trusted_peer.org_id)

    assert protocol.verify_handshake(handshake, bytes.fromhex(trusted_peer.public_key)) is False
    assert await protocol.complete_handshake(handshake, trusted_peer, registry) is False


def test_capability_vector_no_rule_text() -> None:
    rules = [
        RuleStub(category=" Safety ", severity="medium"),
        RuleStub(category="Audit", severity="high"),
    ]

    vector = compute_capability_vector(rules, org_id="org-local")

    assert "rule_text" not in vector.category_severities
    assert "keywords" not in vector.category_severities
    assert "patterns" not in vector.category_severities
    assert vector.category_severities == {"audit": "HIGH", "safety": "MEDIUM"}


def test_capability_vector_severity_aggregation() -> None:
    rules = [
        RuleStub(category="Safety", severity="low"),
        RuleStub(category=" safety ", severity="critical"),
        RuleStub(category="Audit", severity="medium", active=False),
        RuleStub(category="Audit", severity="high"),
    ]

    vector = compute_capability_vector(rules, org_id="org-local", version="2.0")

    assert vector.total_rules == 3
    assert vector.version == "2.0"
    assert vector.category_severities == {"audit": "HIGH", "safety": "CRITICAL"}


def test_intersection_commutative() -> None:
    local = GovernanceCapabilityVector(
        category_severities={"audit": "HIGH", "privacy": "MEDIUM"},
        total_rules=2,
        version="1.0",
        org_id="org-a",
    )
    peer = GovernanceCapabilityVector(
        category_severities={"audit": "CRITICAL", "safety": "LOW"},
        total_rules=3,
        version="1.1",
        org_id="org-b",
    )

    left = compute_intersection(local, peer, MergeSemantic.STRICTEST_WINS)
    right = compute_intersection(peer, local, MergeSemantic.STRICTEST_WINS)

    assert left == right


def test_intersection_strictest_wins() -> None:
    local = GovernanceCapabilityVector(
        category_severities={"audit": "HIGH", "privacy": "MEDIUM"},
        total_rules=2,
        version="1.0",
        org_id="org-a",
    )
    peer = GovernanceCapabilityVector(
        category_severities={"audit": "CRITICAL", "safety": "LOW"},
        total_rules=1,
        version="1.1",
        org_id="org-b",
    )

    merged = compute_intersection(local, peer, MergeSemantic.STRICTEST_WINS)

    assert merged.category_severities == {
        "audit": "CRITICAL",
        "privacy": "MEDIUM",
        "safety": "LOW",
    }


def test_intersection_local_override() -> None:
    local = GovernanceCapabilityVector(
        category_severities={"audit": "HIGH"},
        total_rules=4,
        version="1.0",
        org_id="org-a",
    )
    peer = GovernanceCapabilityVector(
        category_severities={"audit": "CRITICAL", "safety": "LOW"},
        total_rules=2,
        version="1.1",
        org_id="org-b",
    )

    merged = compute_intersection(local, peer, MergeSemantic.LOCAL_OVERRIDE)

    assert merged is local


def test_intersection_union() -> None:
    local = GovernanceCapabilityVector(
        category_severities={"audit": "MEDIUM"},
        total_rules=1,
        version="1.0",
        org_id="org-a",
    )
    peer = GovernanceCapabilityVector(
        category_severities={"audit": "HIGH", "safety": "LOW"},
        total_rules=2,
        version="1.0",
        org_id="org-b",
    )

    merged = compute_intersection(local, peer, MergeSemantic.UNION)

    assert merged.category_severities == {"audit": "HIGH", "safety": "LOW"}
    assert merged.total_rules == 3


def test_serialization_roundtrip(peer: FederationPeer) -> None:
    restored = FederationPeer.from_dict(peer.to_dict())

    assert restored == peer
