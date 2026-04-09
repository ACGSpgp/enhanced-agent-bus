# Governance Path — SCION-style Path-Aware Routing

Authenticated governance paths for the ACGS enhanced agent bus. Messages carry
cryptographic proof of which validators processed them, turning MACI role
separation into a verifiable routing topology.

## Architecture

The package models a governance route as an ordered `GovernancePath` containing
`PathSegment` hops. Each segment records the processing node, its role, the
constitutional hash in effect, the checkpoints completed at that hop, and two
signature fields:

- `prev_signature`: the signature from the immediately preceding hop
- `signature`: an HMAC-SHA256 over the segment's canonical payload plus
  `prev_signature`

That chaining means every hop commits to the entire path history before it.
Changing a prior hop breaks verification for downstream hops as well.

`CheckpointType` defines the canonical governance events that may appear in a
path:

- `CONSTITUTIONAL_HASH`
- `MACI_ROLE_CHECK`
- `IMPACT_SCORING`
- `FULL_VALIDATION`
- `HUMAN_REVIEW`

Verification happens in layers:

1. `GovernancePath.verify_chain()` confirms that each hop links to the expected
   previous signature and that its HMAC recomputes correctly.
2. `GovernancePath.validate_ordering()` ensures the first appearance of each
   checkpoint follows the required governance progression.
3. `MACIPathPolicy.validate_path()` checks that the path satisfies the minimum
   checkpoint set for the selected `RiskTier`.
4. `full_integrity_check()` adds anti-bypass diagnostics for missing
   checkpoints, temporal disorder, and constitutional-hash mismatches.

For transport efficiency, `aggregate_proof()` converts the path into an
`AggregatedProof` whose `merkle_root` summarizes the ordered hop signatures.

## Modules

| Module | Purpose |
|--------|---------|
| `models.py` | `PathSegment`, `GovernancePath`, `CheckpointType` — core data model |
| `policy.py` | `MACIPathPolicy`, `RiskTier` — risk-tiered path requirements |
| `router.py` | `PathAwareRouter` — path-aware message routing |
| `proof.py` | `AggregatedProof`, Merkle tree utilities, proof header encoding |
| `integrity.py` | Anti-bypass detection — signature gaps, missing hops, temporal ordering |

## Quick Start

```python
from enhanced_agent_bus.governance_path import (
    CheckpointType,
    GovernancePath,
    PathSegment,
    aggregate_proof,
    check_signature_chain,
    full_integrity_check,
)
from enhanced_agent_bus.governance_path.policy import RiskTier

key = b"governance-path-test-key"
prev_sig = ""
segments = []

for node_id, role, checks in [
    ("ingress", "EXECUTIVE", (CheckpointType.CONSTITUTIONAL_HASH,)),
    ("validator", "JUDICIAL", (CheckpointType.MACI_ROLE_CHECK,)),
    ("reviewer", "HUMAN", (CheckpointType.IMPACT_SCORING, CheckpointType.HUMAN_REVIEW)),
]:
    segment = PathSegment(
        node_id=node_id,
        node_role=role,
        checks_performed=frozenset(check.value for check in checks),
    )
    prev_sig = segment.sign(key, prev_sig)
    segments.append(segment)

path = GovernancePath(segments=segments)

assert path.verify_chain(key)
assert path.validate_ordering() == (True, None)
assert check_signature_chain(path, key) == []
assert full_integrity_check(path, key, RiskTier.CRITICAL) == []

proof = aggregate_proof(path)
print(proof.merkle_root)
```

If you need a transport-safe summary, serialize the aggregate proof with
`encode_proof_header(proof)` and restore it later with `decode_proof_header(...)`.

## Integration Points

This package is currently self-contained inside `enhanced_agent_bus`; the only
in-tree consumers are its targeted tests. The integration surface is still
clear from the code:

- `PathAwareRouter.route()` and `broadcast()` accept any message-like object or
  dictionary exposing `governance_path` and optional `risk_tier`.
- `AgentMessage` in
  [`packages/enhanced_agent_bus/core_models.py`](../core_models.py) does not
  currently define dedicated governance-path fields, but it already exposes
  extensibility points through `headers`, `metadata`, and generic content
  fields.
- A `MessageProcessor` integration would naturally attach a serialized
  `GovernancePath` to the message before routing, then invoke `MACIPathPolicy`
  or `PathAwareRouter` as part of delivery admission.
- `AggregatedProof` can be serialized with `encode_proof_header()` for use in a
  transport header such as `X-Governance-Proof`. The package does not currently
  define or attach that header automatically; it provides the encoding/decoding
  primitives needed for that integration.

## Security Model

The security design is fail-closed and path-aware:

- HMAC chain integrity: each hop includes `prev_signature` in its signed
  payload, so tampering with an earlier segment invalidates later verification.
- Anti-tamper serialization: `PathSegment.to_dict()` and `GovernancePath.to_dict()`
  preserve the fields needed to reconstruct and re-verify the chain.
- Anti-bypass policy checks: `MACIPathPolicy` requires progressively stronger
  checkpoint coverage as `RiskTier` increases.
- Anti-bypass diagnostics: `full_integrity_check()` reports signature gaps,
  missing required checkpoints, temporal disorder, and constitutional-hash
  mismatches.
- Compact proofing: Merkle aggregation preserves path commitment in a compact
  header-sized structure while still allowing inclusion proofs for individual
  hops.
- Fail-closed routing: `PathAwareRouter` denies delivery when a present
  governance path does not satisfy policy. Messages with no governance path are
  treated as backward-compatible traffic and remain the responsibility of the
  caller's higher-level enforcement policy.
