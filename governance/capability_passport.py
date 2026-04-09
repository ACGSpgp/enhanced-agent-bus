"""ADR-018 capability passport: domain-scoped autonomy levels for AI agents."""
from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class CapabilityDomain(StrEnum):
    """Task domains with independent autonomy assessment (ADR-018)."""

    CODE_REVIEW = "code_review"
    FINANCIAL = "financial"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    GENERAL = "general"  # Backward-compat fallback


DOMAIN_KEYWORDS: dict[CapabilityDomain, list[str]] = {
    CapabilityDomain.FINANCIAL: ["payment", "transfer", "transaction", "invoice", "billing", "fund"],
    CapabilityDomain.SECURITY: ["credential", "secret", "key", "token", "password", "auth", "exploit"],
    CapabilityDomain.INFRASTRUCTURE: ["deploy", "kubernetes", "terraform", "database", "migration", "shutdown"],
    CapabilityDomain.CODE_REVIEW: ["review", "diff", "patch", "lint", "test", "refactor"],
    CapabilityDomain.DOCUMENTATION: ["readme", "docs", "changelog", "docstring", "comment"],
    CapabilityDomain.RESEARCH: ["search", "summarize", "analyze", "compare", "benchmark"],
}


def infer_domain(action_text: str) -> CapabilityDomain:
    """Heuristic domain inference from action text. Falls back to GENERAL."""
    text = action_text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return domain
    return CapabilityDomain.GENERAL


@dataclass
class DomainAutonomy:
    """Binds an agent + domain to a specific autonomy tier."""

    agent_id: str
    domain: CapabilityDomain
    autonomy_tier: str  # AutonomyTier value: "ADVISORY" | "BOUNDED" | "HUMAN_APPROVED"
    certified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    certified_by: str = "system"
    constitutional_hash: str = "608508a9bd224290"
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "autonomy_tier": self.autonomy_tier,
            "certified_at": self.certified_at.isoformat(),
            "certified_by": self.certified_by,
            "constitutional_hash": self.constitutional_hash,
            "evidence": self.evidence,
        }


@dataclass
class CapabilityPassport:
    """Cryptographically signed aggregate of an agent's domain autonomy levels.

    Implements ADR-018: jagged frontier of autonomous vs supervised capabilities.
    """

    agent_id: str
    domains: list[DomainAutonomy] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issued_by: str = "acgs-governance"
    constitutional_hash: str = "608508a9bd224290"
    _signature: str = field(default="", repr=False)

    def get_tier_for_domain(self, domain: CapabilityDomain) -> str:
        """Return the autonomy tier for a domain. Falls back to GENERAL, then HUMAN_APPROVED."""
        for da in self.domains:
            if da.domain == domain:
                return da.autonomy_tier
        # Fallback to GENERAL domain if configured
        for da in self.domains:
            if da.domain == CapabilityDomain.GENERAL:
                return da.autonomy_tier
        # Default: require human approval (fail-closed)
        return "HUMAN_APPROVED"

    def get_tier_for_action(self, action_text: str) -> str:
        """Infer domain from action text and return the appropriate autonomy tier."""
        domain = infer_domain(action_text)
        return self.get_tier_for_domain(domain)

    def _compute_signature(self, secret: str | None = None) -> str:
        """Compute HMAC-SHA256 signature without mutating state."""
        resolved = secret or os.environ.get("ACGS2_SERVICE_SECRET", "")
        if not resolved:
            raise ValueError(
                "ACGS2_SERVICE_SECRET environment variable must be set to sign/verify passports"
            )
        key = resolved.encode()
        payload = json.dumps(
            {
                "agent_id": self.agent_id,
                "domains": [d.to_dict() for d in self.domains],
                "issued_at": self.issued_at.isoformat(),
                "constitutional_hash": self.constitutional_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hmac.new(key, payload.encode(), "sha256").hexdigest()

    def sign(self, secret: str | None = None) -> str:
        """HMAC-SHA256 sign the passport. Returns and stores signature."""
        self._signature = self._compute_signature(secret)
        return self._signature

    def verify(self, secret: str | None = None) -> bool:
        """Verify the passport signature."""
        expected = self._compute_signature(secret)
        return hmac.compare_digest(expected, self._signature)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "domains": [d.to_dict() for d in self.domains],
            "issued_at": self.issued_at.isoformat(),
            "issued_by": self.issued_by,
            "constitutional_hash": self.constitutional_hash,
            "signature": self._signature,
        }


class PassportRegistry:
    """In-memory registry of capability passports. Production would use DB."""

    def __init__(self) -> None:
        self._passports: dict[str, CapabilityPassport] = {}

    def register(self, passport: CapabilityPassport) -> None:
        passport.sign()
        self._passports[passport.agent_id] = passport

    def get(self, agent_id: str) -> CapabilityPassport | None:
        return self._passports.get(agent_id)

    def get_tier(self, agent_id: str, action_text: str) -> str:
        """Get the autonomy tier for an agent+action. Fail-closed: HUMAN_APPROVED if no passport."""
        passport = self._passports.get(agent_id)
        if passport is None:
            return "HUMAN_APPROVED"
        # Verify signature before trusting the passport's domain tiers.
        try:
            valid = passport.verify()
        except Exception:
            valid = False
        if not valid:
            return "HUMAN_APPROVED"
        return passport.get_tier_for_action(action_text)

    def create_default_passport(
        self,
        agent_id: str,
        default_tier: str = "BOUNDED",
    ) -> CapabilityPassport:
        """Create a passport with GENERAL domain set to default_tier."""
        passport = CapabilityPassport(
            agent_id=agent_id,
            domains=[
                DomainAutonomy(
                    agent_id=agent_id,
                    domain=CapabilityDomain.GENERAL,
                    autonomy_tier=default_tier,
                )
            ],
        )
        self.register(passport)
        return passport


# Module-level singleton for lightweight usage
_default_registry: PassportRegistry | None = None


def get_passport_registry() -> PassportRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PassportRegistry()
    return _default_registry


def reset_passport_registry() -> None:
    """Reset the module-level singleton. Use only in tests."""
    global _default_registry
    _default_registry = None
