---
name: eab-stop-gate-review
description: Review the immediately previous enhanced-agent-bus code-changing turn for governance, security, namespace, and verification risks.
disable-model-invocation: true
---

# EAB Stop-Gate Review

Use only for reviewing the immediately previous code-changing turn. If the previous turn did not edit code or automation files, return `ALLOW:` immediately and do no substantive review.

## Review Priorities

Lead with `ALLOW:` or `BLOCK:`.

Inspect only the files changed by the previous turn. Do not review unrelated dirty worktree state.

Block on:

- New fail-open behavior in auth, MACI, OPA, policy, governance, or capability passport paths.
- JWT algorithm parsing that bypasses `enhanced_agent_bus._compat.security.jwt_algorithms.resolve_jwt_algorithm`.
- New imports from deleted namespace `enhanced_agent_bus.middleware`.
- New code preferring legacy `context/` over canonical `context_memory/`.
- Cross-domain imports between `persistence/` and `saga_persistence/`.
- Edits to generated artifacts, cache output, coverage output, or build output.
- Verification claims not supported by command output.
- Type discipline regressions, especially new untyped public functions in strict cohorts.

## Output Shape

```text
ALLOW: <short reason>
```

or

```text
BLOCK: <short reason>

Findings:
- <severity> <file:line> <specific issue and why it matters>

Verification:
- <commands reviewed or missing>
```

Keep summaries secondary to findings.
