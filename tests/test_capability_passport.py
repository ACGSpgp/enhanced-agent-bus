"""Tests for ADR-018 capability passport."""
import os
from unittest.mock import patch

import pytest

from enhanced_agent_bus.governance.capability_passport import (
    CapabilityDomain,
    CapabilityPassport,
    DomainAutonomy,
    PassportRegistry,
    get_passport_registry,
    infer_domain,
    reset_passport_registry,
)

# ---------------------------------------------------------------------------
# infer_domain — all domains
# ---------------------------------------------------------------------------


def test_infer_domain_financial():
    assert infer_domain("transfer funds to account") == CapabilityDomain.FINANCIAL


def test_infer_domain_security():
    assert infer_domain("rotate API token credentials") == CapabilityDomain.SECURITY


def test_infer_domain_infrastructure():
    assert infer_domain("deploy kubernetes cluster") == CapabilityDomain.INFRASTRUCTURE


def test_infer_domain_code_review():
    assert infer_domain("review this diff") == CapabilityDomain.CODE_REVIEW


def test_infer_domain_documentation():
    assert infer_domain("update the changelog") == CapabilityDomain.DOCUMENTATION


def test_infer_domain_research():
    assert infer_domain("analyze and compare these benchmarks") == CapabilityDomain.RESEARCH


def test_infer_domain_fallback():
    assert infer_domain("do something vague") == CapabilityDomain.GENERAL


def test_infer_domain_case_insensitive():
    assert infer_domain("PAYMENT processing") == CapabilityDomain.FINANCIAL


# ---------------------------------------------------------------------------
# CapabilityPassport — tier routing
# ---------------------------------------------------------------------------


def test_capability_passport_domain_routing():
    passport = CapabilityPassport(
        agent_id="test-agent",
        domains=[
            DomainAutonomy("test-agent", CapabilityDomain.CODE_REVIEW, "ADVISORY"),
            DomainAutonomy("test-agent", CapabilityDomain.FINANCIAL, "HUMAN_APPROVED"),
        ],
    )
    assert passport.get_tier_for_domain(CapabilityDomain.CODE_REVIEW) == "ADVISORY"
    assert passport.get_tier_for_domain(CapabilityDomain.FINANCIAL) == "HUMAN_APPROVED"
    # Unknown domain → fail-closed
    assert passport.get_tier_for_domain(CapabilityDomain.SECURITY) == "HUMAN_APPROVED"


def test_capability_passport_action_routing():
    passport = CapabilityPassport(
        agent_id="test-agent",
        domains=[
            DomainAutonomy("test-agent", CapabilityDomain.CODE_REVIEW, "ADVISORY"),
            DomainAutonomy("test-agent", CapabilityDomain.FINANCIAL, "HUMAN_APPROVED"),
        ],
    )
    assert passport.get_tier_for_action("review this diff") == "ADVISORY"
    assert passport.get_tier_for_action("process payment transfer") == "HUMAN_APPROVED"


def test_passport_general_domain_fallback():
    """If specific domain absent but GENERAL is configured, use GENERAL tier."""
    passport = CapabilityPassport(
        agent_id="fallback-agent",
        domains=[
            DomainAutonomy("fallback-agent", CapabilityDomain.GENERAL, "BOUNDED"),
        ],
    )
    # Security domain not explicitly configured → falls back to GENERAL
    assert passport.get_tier_for_domain(CapabilityDomain.SECURITY) == "BOUNDED"


def test_passport_no_domains_fail_closed():
    """Empty passport → HUMAN_APPROVED for all domains."""
    passport = CapabilityPassport(agent_id="empty-agent", domains=[])
    assert passport.get_tier_for_domain(CapabilityDomain.FINANCIAL) == "HUMAN_APPROVED"
    assert passport.get_tier_for_domain(CapabilityDomain.GENERAL) == "HUMAN_APPROVED"


# ---------------------------------------------------------------------------
# Signing and verification
# ---------------------------------------------------------------------------


def test_passport_signing():
    passport = CapabilityPassport(agent_id="signed-agent")
    sig = passport.sign(secret="test-secret")
    assert len(sig) == 64  # SHA256 hex
    assert passport.verify(secret="test-secret")
    assert not passport.verify(secret="wrong-secret")


def test_passport_sign_no_secret_raises_without_env(monkeypatch):
    """_compute_signature raises ValueError when ACGS2_SERVICE_SECRET unset."""
    monkeypatch.delenv("ACGS2_SERVICE_SECRET", raising=False)
    passport = CapabilityPassport(agent_id="no-secret")
    with pytest.raises(ValueError, match="ACGS2_SERVICE_SECRET"):
        passport.sign()


def test_passport_sign_uses_env_secret(monkeypatch):
    monkeypatch.setenv("ACGS2_SERVICE_SECRET", "env-test-secret")
    passport = CapabilityPassport(agent_id="env-agent")
    sig = passport.sign()
    assert len(sig) == 64
    assert passport.verify()


def test_passport_tamper_detection():
    """Modifying domain list after signing invalidates the signature."""
    passport = CapabilityPassport(
        agent_id="tamper-target",
        domains=[
            DomainAutonomy("tamper-target", CapabilityDomain.CODE_REVIEW, "ADVISORY"),
        ],
    )
    passport.sign(secret="signing-secret")
    assert passport.verify(secret="signing-secret")

    # Tamper: add a new domain
    passport.domains.append(DomainAutonomy("tamper-target", CapabilityDomain.FINANCIAL, "BOUNDED"))
    assert not passport.verify(secret="signing-secret")


def test_passport_to_dict_has_signature():
    passport = CapabilityPassport(agent_id="dict-agent")
    passport.sign(secret="dict-secret")
    d = passport.to_dict()
    assert "signature" in d
    assert len(d["signature"]) == 64
    assert d["agent_id"] == "dict-agent"
    assert isinstance(d["domains"], list)


# ---------------------------------------------------------------------------
# PassportRegistry
# ---------------------------------------------------------------------------


def test_passport_registry_fail_closed():
    registry = PassportRegistry()
    # No passport registered → HUMAN_APPROVED
    assert registry.get_tier("unknown-agent", "any action") == "HUMAN_APPROVED"


def test_passport_registry_lookup():
    registry = PassportRegistry()
    registry.create_default_passport("agent-1", default_tier="BOUNDED")
    assert registry.get_tier("agent-1", "something general") == "BOUNDED"


def test_passport_registry_invalid_passport_fail_closed(monkeypatch):
    """A passport whose signature doesn't verify → HUMAN_APPROVED from get_tier."""
    monkeypatch.setenv("ACGS2_SERVICE_SECRET", "registry-secret")
    registry = PassportRegistry()
    passport = registry.create_default_passport("tampered-agent", default_tier="ADVISORY")

    # Tamper after registration
    passport.domains.append(DomainAutonomy("tampered-agent", CapabilityDomain.FINANCIAL, "ADVISORY"))

    # get_tier must re-verify and fail-close
    assert registry.get_tier("tampered-agent", "transfer funds") == "HUMAN_APPROVED"


def test_passport_registry_get_returns_passport():
    registry = PassportRegistry()
    registry.create_default_passport("fetch-agent", default_tier="BOUNDED")
    fetched = registry.get("fetch-agent")
    assert fetched is not None
    assert fetched.agent_id == "fetch-agent"


def test_passport_registry_get_missing_returns_none():
    registry = PassportRegistry()
    assert registry.get("nonexistent") is None


def test_passport_registry_create_default_general_domain():
    registry = PassportRegistry()
    passport = registry.create_default_passport("gen-agent", default_tier="ADVISORY")
    assert len(passport.domains) == 1
    assert passport.domains[0].domain == CapabilityDomain.GENERAL
    assert passport.domains[0].autonomy_tier == "ADVISORY"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def test_get_passport_registry_returns_singleton():
    reset_passport_registry()
    r1 = get_passport_registry()
    r2 = get_passport_registry()
    assert r1 is r2


def test_reset_passport_registry_clears_state():
    reset_passport_registry()
    reg = get_passport_registry()
    reg.create_default_passport("to-be-cleared", default_tier="BOUNDED")
    assert reg.get("to-be-cleared") is not None

    reset_passport_registry()
    fresh = get_passport_registry()
    assert fresh.get("to-be-cleared") is None
