"""Shim package for src.core.shared.security.

JWT governance rule:
- New enhanced-agent-bus JWT entry points should normalize algorithms through
  ``enhanced_agent_bus._compat.security.jwt_algorithms.resolve_jwt_algorithm``.
- Only keep a module-local JWT posture when it is intentionally narrower than
  the shared helper and clearly documented.
"""

from __future__ import annotations

from enhanced_agent_bus._compat.security.error_sanitizer import *  # noqa: F403
