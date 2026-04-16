# Constitutional Hash: 608508a9bd224290
"""Optional SpacetimeDB Real-Time Governance Integration.

Not re-exported in ``__init__.py`` — experimental. Import directly if needed.
"""

try:
    from .persistence.spacetime_client import (
        GovernanceEvent,
        GovernanceEventType,
        GovernanceStateClient,
        SpacetimeConfig,
    )

    SPACETIMEDB_AVAILABLE = True
except ImportError:
    SPACETIMEDB_AVAILABLE = False
    GovernanceEvent = object  # type: ignore[assignment, misc]
    GovernanceEventType = object  # type: ignore[assignment, misc]
    GovernanceStateClient = object  # type: ignore[assignment, misc]
    SpacetimeConfig = object  # type: ignore[assignment, misc]

_EXT_ALL = [
    "SPACETIMEDB_AVAILABLE",
    "GovernanceEvent",
    "GovernanceEventType",
    "GovernanceStateClient",
    "SpacetimeConfig",
]
