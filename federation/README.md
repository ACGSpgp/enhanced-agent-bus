# Federation — Cross-Organizational Governance

Federated governance infrastructure for the ACGS enhanced agent bus. Organizations
exchange constitutional metadata and compute governance intersections without
exposing raw rules, enabling cross-org agent interactions with bilateral
accountability.

## Architecture

`FederationPeer` captures discoverable peer metadata such as organization ID,
constitutional hash, advertised capabilities, Kafka routing prefix, and trust
level. `FederationRegistry` manages the async peer lifecycle around
registration, heartbeats, and lease expiry.

`FederationProtocol` performs a mutual HMAC challenge-response handshake.
Initiators create a nonce-like challenge, responders sign it with shared key
material, and verifiers fail closed on status or signature mismatches before any
peer is admitted into the registry.

`GovernanceCapabilityVector` is the privacy-preserving governance summary used
for cross-org compatibility checks. It contains only normalized categories,
severities, metadata, and total active rule count. It intentionally excludes
rule text, keywords, patterns, or other rule internals.

`MergeSemantic` defines how two organizations reconcile governance posture.
`STRICTEST_WINS` yields a fail-closed bilateral envelope, `LOCAL_OVERRIDE`
preserves unilateral local policy, and `UNION` retains the combined category
surface with strict overlap handling.

## Modules

| Module | Contents | Purpose |
| --- | --- | --- |
| `models.py` | `FederationPeer`, `FederationHandshake`, `GovernanceCapabilityVector`, `TrustLevel` | Canonical federation data model definitions. |
| `registry.py` | `FederationRegistry` | Async peer lifecycle management for discovery, heartbeats, and expiry. |
| `handshake.py` | `FederationProtocol` | Mutual HMAC challenge-response used to establish bilateral trust. |
| `intersection.py` | Capability vector computation and `MergeSemantic` | Privacy-preserving coverage summarization and merge semantics. |
| `bilateral_audit.py` | `BilateralAuditLog` and bilateral signature helpers | Cross-org tamper-evident audit trail for bilateral operations. |
| `policy_learning.py` | `ViolationSignal`, `PolicyLearningChannel`, `AmendmentSuggestion` | Privacy-preserving violation signals with differential privacy. |

## Quick Start

```python
from enhanced_agent_bus.federation import (
    BilateralAuditEntry,
    BilateralAuditLog,
    FederationPeer,
    FederationProtocol,
    FederationRegistry,
    MergeSemantic,
    TrustLevel,
    compute_capability_vector,
    compute_intersection,
    sign_bilateral_entry,
)


async def main() -> None:
    registry = FederationRegistry()
    protocol = FederationProtocol()

    peer = FederationPeer(
        org_id="org-bravo",
        constitutional_hash="608508a9bd224290",
        public_key=bytes.fromhex("22" * 32).hex(),
        capabilities=frozenset({"governance", "audit"}),
        kafka_topic_prefix="bravo.gov",
        trust_level=TrustLevel.VERIFIED,
    )

    handshake = protocol.initiate_handshake("org-alpha", peer.org_id)
    protocol.respond_to_handshake(handshake, bytes.fromhex(peer.public_key))
    assert protocol.verify_handshake(handshake, bytes.fromhex(peer.public_key))
    assert await protocol.complete_handshake(handshake, peer, registry)

    local_rules = [
        type("Rule", (), {"category": "Safety", "severity": "HIGH", "active": True})(),
        type("Rule", (), {"category": "Privacy", "severity": "MEDIUM", "active": True})(),
    ]
    peer_rules = [
        type("Rule", (), {"category": "Safety", "severity": "CRITICAL", "active": True})(),
    ]

    local_vector = compute_capability_vector(local_rules, org_id="org-alpha")
    peer_vector = compute_capability_vector(peer_rules, org_id=peer.org_id)
    intersection = compute_intersection(
        local_vector,
        peer_vector,
        MergeSemantic.STRICTEST_WINS,
    )

    audit_log = BilateralAuditLog()
    entry = BilateralAuditEntry(
        local_org_id="org-alpha",
        peer_org_id=peer.org_id,
        action_summary=f"Computed intersection for {sorted(intersection.category_severities)}",
        local_constitutional_hash="608508a9bd224290",
        peer_constitutional_hash=peer.constitutional_hash,
        local_signature="",
    )
    signed_entry = BilateralAuditEntry(
        **{
            **entry.to_dict(),
            "local_signature": sign_bilateral_entry(entry, b"local-secret"),
        }
    )
    await audit_log.record(signed_entry)
```

## Privacy Model

`GovernanceCapabilityVector` contains no rule text, keywords, or patterns. It
shares only normalized category severities, a total rule count, version
metadata, and organization metadata.

`ViolationSignal` contains no `matched_content` or `rule_id`. Signal generation
reduces raw events to category, severity, frequency bucket, temporal trend, and
time-window metadata.

Differential privacy is configurable through `epsilon` in
`apply_differential_privacy`. Lower epsilon increases bucket perturbation and
higher epsilon approaches the original aggregate.

Amendment influence is capped at 10% by default via
`generate_amendment_suggestions(..., max_peer_influence=0.1)`.

## Security Model

The handshake model uses HMAC challenge-response to prove possession of shared
key material before a peer is registered.

Trust levels gate which peers are treated as sufficiently trustworthy for
federation workflows.

Signature mismatch is fail-closed: incomplete or invalid handshakes do not
register peers, and bilateral signature verification uses constant-time digest
comparison.

Bilateral audit entries support non-repudiation by preserving local and peer
signatures over a canonical payload.

## Known Limitations

- Schema compatibility is currently stubbed at the Kafka integration boundary.
- Constitutional hash completeness is insufficient as a federation trust signal;
  use capability vectors for cross-org compatibility decisions instead.
- Tenant isolation still needs a parallel federation boundary model for strict
  multi-tenant deployments.
