"""Path-aware routing helpers for the enhanced agent bus.

The router in this module treats governance evidence as part of routing
eligibility. Messages that carry a governance path are admitted only when the
attached path satisfies the configured MACI policy for the message risk tier.
Messages without a governance path remain backward compatible and are allowed by
default.
"""

from __future__ import annotations

from typing import Any

from .models import GovernancePath
from .policy import MACIPathPolicy, RiskTier


class PathAwareRouter:
    """Router that fail-closes when governance path requirements are not met.

    Use this router in front of delivery logic when a message may carry
    ``governance_path`` and ``risk_tier`` fields. It accepts either object-like
    messages or dictionaries and delegates path validation to
    :class:`MACIPathPolicy`.

    Invariants:
        - Invalid governance paths block routing.
        - Missing governance paths are treated as backward-compatible traffic.
        - Registry access is capability-based and checked at runtime.
    """

    def __init__(self, policy: MACIPathPolicy | None = None) -> None:
        """Initialize the router with a policy object.

        Args:
            policy: Optional policy implementation. When omitted, the default
                ``MACIPathPolicy`` is used.
        """
        self._policy = policy or MACIPathPolicy()

    async def route(self, message: Any, registry: Any) -> str | None:
        """Resolve a single destination agent when the path policy allows it.

        Args:
            message: Message-like object or dictionary carrying routing fields.
            registry: Registry-like object that can check whether an agent
                exists.

        Returns:
            The destination agent identifier when the message is admissible and
            the target exists, otherwise ``None``.
        """
        if not self._is_path_allowed(message):
            return None

        target = getattr(message, "to_agent", None)
        if not target:
            return None

        if await self._registry_has_agent(registry, target):
            return target
        return None

    async def broadcast(
        self, message: Any, registry: Any, exclude: set[str] | None = None
    ) -> list[str]:
        """List eligible broadcast destinations when the path policy allows it.

        Args:
            message: Message-like object or dictionary carrying routing fields.
            registry: Registry-like object that can list candidate agents.
            exclude: Optional set of agent identifiers that must not receive the
                broadcast.

        Returns:
            A list of recipient agent identifiers. The sender is automatically
            excluded when present on the message.
        """
        if not self._is_path_allowed(message):
            return []

        excluded = set(exclude or set())
        sender = getattr(message, "from_agent", None)
        if sender:
            excluded.add(sender)

        return [
            agent_id
            for agent_id in await self._registry_list_agents(registry)
            if agent_id not in excluded
        ]

    def _is_path_allowed(self, message: Any) -> bool:
        path = self._extract_path(message)
        if path is None:
            return True

        risk_tier = self._extract_risk_tier(message)
        is_valid, _ = self._policy.validate_path(path, risk_tier)
        return is_valid

    def _extract_path(self, message: Any) -> GovernancePath | None:
        raw_path = getattr(message, "governance_path", None)
        if raw_path is None and isinstance(message, dict):
            raw_path = message.get("governance_path")
        if raw_path is None:
            return None
        if isinstance(raw_path, GovernancePath):
            return raw_path
        if isinstance(raw_path, dict):
            return GovernancePath.from_dict(raw_path)
        return None

    def _extract_risk_tier(self, message: Any) -> RiskTier:
        raw_tier = getattr(message, "risk_tier", None)
        if raw_tier is None and isinstance(message, dict):
            raw_tier = message.get("risk_tier")
        if isinstance(raw_tier, RiskTier):
            return raw_tier
        if isinstance(raw_tier, str):
            normalized = raw_tier.strip().lower()
            for tier in RiskTier:
                if normalized in {tier.name.lower(), tier.value.lower()}:
                    return tier
        return RiskTier.LOW

    async def _registry_has_agent(self, registry: Any, agent_id: str) -> bool:
        exists = getattr(registry, "exists", None)
        if callable(exists):
            return bool(await exists(agent_id))
        get_agent = getattr(registry, "get", None)
        if callable(get_agent):
            return (await get_agent(agent_id)) is not None
        return False

    async def _registry_list_agents(self, registry: Any) -> list[str]:
        list_agents = getattr(registry, "list_agents", None)
        if callable(list_agents):
            return list(await list_agents())
        return []
