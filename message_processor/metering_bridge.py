"""Metering-bridge surface for message_processor (Cat 5 split).

Thin re-export module: concentrates metering integration symbols
(``_metering_integration`` conditional import, ``_enable_metering`` /
``_metering_hooks`` attributes on MessageProcessor, and ``get_metering_hooks``
bridge). No behavior change.
"""

from __future__ import annotations

from enhanced_agent_bus.message_processor import MessageProcessor

__all__ = ["MessageProcessor"]
