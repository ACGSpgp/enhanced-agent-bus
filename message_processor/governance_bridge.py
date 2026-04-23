"""Governance-bridge surface for message_processor (Cat 5 split).

Thin re-export module: concentrates governance orchestration symbols
(``_build_verification_orchestrator``, ``_build_verification_runtime_dependencies``,
the ``_governance_*`` setup attributes on MessageProcessor) alongside the
:class:`GovernanceCoordinator` dependency. No behavior change.
"""

from __future__ import annotations

from enhanced_agent_bus.governance_coordinator import GovernanceCoordinator

from enhanced_agent_bus.message_processor import MessageProcessor

__all__ = ["GovernanceCoordinator", "MessageProcessor"]
