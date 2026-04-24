"""Cat 8 fail-closed coverage for OPA client.

Verifies that `check_agent_authorization` and `evaluate_policy` deny
(return False / allowed=False) when the underlying OPA call times out
or when the constitutional hash is mismatched. The invariant under test
is fail-closed semantics: network/timeout errors MUST NOT yield allow=True.

These tests run unconditionally (unlike test_opa_client_coverage.py which
is env-gated) because the fail-closed invariant is a security property
that must never regress.
"""

from __future__ import annotations

import pytest
from httpx import TimeoutException as HTTPTimeoutException

from enhanced_agent_bus.opa_client.core import OPAClient


@pytest.mark.asyncio
async def test_check_agent_authorization_fails_closed_on_timeout(monkeypatch):
    client = OPAClient(opa_url="http://localhost:9", timeout=0.01, enable_cache=False)

    async def _raise_timeout(*_args, **_kwargs):
        raise HTTPTimeoutException("simulated OPA timeout")

    monkeypatch.setattr(client, "evaluate_policy", _raise_timeout)

    allowed = await client.check_agent_authorization(
        agent_id="agent-1",
        action="read",
        resource="resource-1",
        context=None,
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_check_agent_authorization_denies_on_constitutional_hash_mismatch():
    client = OPAClient(opa_url="http://localhost:9", enable_cache=False)

    allowed = await client.check_agent_authorization(
        agent_id="agent-1",
        action="read",
        resource="resource-1",
        context={"constitutional_hash": "wrong-hash"},
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_evaluate_policy_fails_closed_on_timeout(monkeypatch):
    client = OPAClient(opa_url="http://localhost:9", timeout=0.01, enable_cache=False)

    async def _raise_timeout(*_args, **_kwargs):
        raise HTTPTimeoutException("simulated OPA timeout")

    monkeypatch.setattr(client, "_dispatch_evaluation", _raise_timeout)

    result = await client.evaluate_policy(
        input_data={"agent_id": "a", "action": "read", "resource": "r"},
        policy_path="data.acgs.rbac.allow",
    )

    assert result.get("allowed") is False
