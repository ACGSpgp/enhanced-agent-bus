# OpenEvolve Adapter - Agent Guide

Scope: `enhanced_agent_bus/openevolve_adapter/`.

This adapter bridges OpenEvolve-compatible mutation loops into ACGS governance.
It scores candidates, enforces MACI separation, gates rollout stage by risk, and
exposes CLI/message-processor integration.

## Local Contracts

- `GovernedEvolver` is the proposer. It must receive a verifier by constructor
  injection and must never construct its own validator.
- The injected verifier is the MACI validator boundary. Re-verify on every
  evolution call; do not trust cached candidate payloads.
- `RolloutController` decides whether rollout is allowed; it must not execute
  rollout side effects.
- `EvolutionCandidate.__post_init__` owns hash, payload, and risk-tier invariants.
  Do not bypass it with low-level object mutation.
- `CascadeEvaluator` should keep cheap checks before expensive full verification.

## Files

| Task | File |
| --- | --- |
| Candidate wire contract | `candidate.py` |
| 60/40 performance/compliance scoring | `fitness.py` |
| MACI-enforced evolution loop | `evolver.py` |
| Risk-tier rollout gate | `rollout.py` |
| Progressive evaluation pipeline | `cascade.py` |
| MessageProcessor integration | `integration.py` |
| CLI commands | `cli.py` |

## Verification

```bash
python -m pytest openevolve_adapter/tests/ -q --import-mode=importlib
python -m ruff check openevolve_adapter
python -m py_compile $(find openevolve_adapter -name '*.py' -print)
```

## Anti-Patterns

- Self-validation inside `GovernedEvolver`.
- Ignoring `RolloutController.gate()` decisions.
- Using `_StubVerifier` outside tests.
- Changing risk-tier constraints without updating tests and operator-facing docs.
