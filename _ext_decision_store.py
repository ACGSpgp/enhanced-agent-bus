# Constitutional Hash: 608508a9bd224290
"""Optional Decision Store for FR-12 Decision Explanation API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .decision_store import (
        DecisionStore,
        get_decision_store,
        reset_decision_store,
    )
    DECISION_STORE_AVAILABLE = True
else:
    try:
        from .decision_store import (
            DecisionStore,
            get_decision_store,
            reset_decision_store,
        )

        DECISION_STORE_AVAILABLE = True
    except ImportError:
        DECISION_STORE_AVAILABLE = False
        DecisionStore = object
        get_decision_store = object
        reset_decision_store = object

_EXT_ALL = [
    "DECISION_STORE_AVAILABLE",
    "DecisionStore",
    "get_decision_store",
    "reset_decision_store",
]
