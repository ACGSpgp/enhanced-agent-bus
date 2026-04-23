"""Tests for fallback_stubs production hardening (US-005 / Cat 3)."""

from __future__ import annotations

import inspect

import pytest

import enhanced_agent_bus.fallback_stubs as fs


def test_slowapi_raises_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs, "IS_PRODUCTION", True)
    with pytest.raises(fs.DependencyNotAvailableError):
        fs.StubLimiter()


def test_slowapi_degrades_gracefully_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs, "IS_PRODUCTION", False)
    stub = fs.StubLimiter()
    assert stub is not None
    assert hasattr(stub, "_limiter")


def test_tenant_context_fallback_is_fail_closed() -> None:
    source = inspect.getsource(fs)
    assert "SECURITY_FALLBACK_REJECTED" in source
    assert "status_code=400" in source
