# JWT Environment Precedence

This note documents the JWT algorithm environment-variable behavior inside
`enhanced_agent_bus`.

It focuses on the modules that still resolve JWT algorithms directly at runtime
or have module-specific JWT posture:

- tenant routes
- collaboration API
- session governance SDK

## Summary Table

| Module | Variable(s) | Effective behavior | Default |
| --- | --- | --- | --- |
| `routes/tenants.py` | `JWT_ALGORITHM` | Uses shared compat normalization via `_configured_jwt_algorithm()` | `RS256` |
| `collaboration/api_integration.py` | `COLLABORATION_JWT_ALGORITHM` | Explicitly `HS256`-only because validation uses `COLLABORATION_SECRET_KEY` | `HS256` |
| `enterprise_sso/session_governance_sdk.py` | `SESSION_JWT_ALGORITHM` | Uses shared compat normalization for session token signing/verification | `RS256` |

## Module Posture

### Tenant Routes

File: [`routes/tenants.py`](../routes/tenants.py)

- Reads `JWT_ALGORITHM`
- Canonicalizes through the compat JWT helper
- Validates bearer JWTs with `JWT_SECRET_KEY`
- Current route tests exercise `HS256` successfully

Practical meaning:

- tenant-route JWT behavior now matches its runtime/tests
- `HS256` is a valid tenant-route setting
- invalid values fail early through the shared compat resolver

### Collaboration API

File: [`collaboration/api_integration.py`](../collaboration/api_integration.py)

- Reads `COLLABORATION_JWT_ALGORITHM`
- Does **not** inherit `JWT_ALGORITHM`
- Accepts only `HS256`
- Uses `COLLABORATION_SECRET_KEY` as the verification secret

Practical meaning:

- this module is intentionally isolated from global JWT algorithm changes
- setting `JWT_ALGORITHM=RS256` does nothing for collaboration auth
- if asymmetric JWT verification is ever needed here, key-loading support must
  be added before widening the allowlist

### Session Governance SDK

File: [`enterprise_sso/session_governance_sdk.py`](../enterprise_sso/session_governance_sdk.py)

- Reads `SESSION_JWT_ALGORITHM`
- Canonicalizes through the compat JWT helper
- Keeps its own issuer/audience variables:
  - `SESSION_JWT_ISSUER`
  - `SESSION_JWT_AUDIENCE`

Practical meaning:

- session JWT posture is intentionally independent from tenant routes and
  collaboration auth
- changing `JWT_ALGORITHM` alone does not reconfigure session tokens

## Migration Guidance

Use explicit variables when different JWT surfaces need different behavior:

```bash
JWT_ALGORITHM=HS256
SESSION_JWT_ALGORITHM=RS256
COLLABORATION_JWT_ALGORITHM=HS256
```

Recommended operator guidance:

- use `JWT_ALGORITHM` for tenant-route style shared bus auth
- use `SESSION_JWT_ALGORITHM` only for session-governance tokens
- leave `COLLABORATION_JWT_ALGORITHM` at `HS256` unless the module is extended
  to support asymmetric key verification

## Findings From Repo Scan

- No checked-in deployment manifest in this repository currently documents all
  three variables together.
- The main operator risk was silent assumption drift:
  - tenant routes historically behaved as if `HS256` was valid while carrying a
    narrower module-local allowlist
  - collaboration historically looked asymmetric-friendly while actually using a
    shared-secret verifier

## Follow-Up Triggers

Update this document when:

- tenant routes stop using `JWT_ALGORITHM`
- collaboration adds public-key / asymmetric JWT support
- session governance starts inheriting a broader shared JWT setting
