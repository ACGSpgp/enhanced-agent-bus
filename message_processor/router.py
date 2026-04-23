"""Router surface for message_processor (Cat 5 split).

Thin re-export module: concentrates the top-level routing surface
(``MessageProcessor`` class) that clients import to route agent messages.
No behavior change.
"""

from __future__ import annotations

from enhanced_agent_bus.message_processor import MessageProcessor

__all__ = ["MessageProcessor"]
