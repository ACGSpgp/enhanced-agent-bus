"""
MACI Import Management
Constitutional Hash: 608508a9bd224290

Centralizes optional dependency imports for MACI enforcement.
Provides clean fallback handling for imports that may not be available
in all contexts (e.g., standalone testing, minimal deployments).

This module eliminates fragile triple-nested try/except import blocks
by providing a single source of truth for MACI dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict

    from .models import AgentMessage as AgentMessage
    from .models import MessageType as MessageType
else:
    try:
        from enhanced_agent_bus._compat.types import JSONDict
    except ImportError:
        JSONDict = dict[str, Any]

from enhanced_agent_bus.observability.structured_logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Feature Availability Flags
# =============================================================================

MACI_CORE_AVAILABLE: bool = False
OBSERVABILITY_AVAILABLE: bool = False
GLOBAL_SETTINGS_AVAILABLE: bool = False

# =============================================================================
# Default Values for Fallbacks
# =============================================================================

try:
    from enhanced_agent_bus._compat.constants import (
        CONSTITUTIONAL_HASH as _DEFAULT_CONSTITUTIONAL_HASH,
    )
except ImportError:
    _DEFAULT_CONSTITUTIONAL_HASH = "608508a9bd224290"  # pragma: allowlist secret

CONSTITUTIONAL_HASH: str = _DEFAULT_CONSTITUTIONAL_HASH


def _load_global_settings() -> object | None:
    try:
        from enhanced_agent_bus._compat.config import settings as configured_settings
    except ImportError as exc:
        logger.debug(f"Global settings unavailable: {exc}")
        return None
    global GLOBAL_SETTINGS_AVAILABLE  # noqa: PLW0603
    GLOBAL_SETTINGS_AVAILABLE = True
    return cast(object, configured_settings)


global_settings = _load_global_settings()


def _build_exception_stubs() -> tuple[
    type[Exception],
    type[Exception],
    type[Exception],
    type[Exception],
    type[Exception],
]:
    class _MACIStubBaseError(Exception):
        """Fallback base error when shared compat errors are unavailable."""

        pass

    class _MACIErrorStub(_MACIStubBaseError):
        http_status_code = 403
        error_code = "MACI_ERROR"

    class _MACIRoleViolationErrorStub(_MACIErrorStub):
        error_code = "MACI_ROLE_VIOLATION"

        def __init__(
            self,
            agent_id: str,
            role: str,
            action: str,
            allowed_roles: list[str] | None = None,
        ) -> None:
            self.agent_id = agent_id
            self.role = role
            self.action = action
            self.allowed_roles = allowed_roles or []
            message = f"Agent '{agent_id}' ({role}) cannot perform '{action}'"
            super().__init__(message)

    class _MACISelfValidationErrorStub(_MACIErrorStub):
        error_code = "MACI_SELF_VALIDATION"

        def __init__(self, agent_id: str, action: str, output_id: str | None = None) -> None:
            self.agent_id = agent_id
            self.action = action
            self.output_id = output_id
            message = f"Agent '{agent_id}' cannot {action} its own output"
            super().__init__(message)

    class _MACICrossRoleValidationErrorStub(_MACIErrorStub):
        error_code = "MACI_CROSS_ROLE_VALIDATION"

        def __init__(
            self,
            agent_id: str,
            agent_role: str,
            target_id: str,
            target_role: str,
            reason: str,
        ) -> None:
            self.agent_id = agent_id
            self.agent_role = agent_role
            self.target_id = target_id
            self.target_role = target_role
            self.reason = reason
            message = (
                f"Cross-role validation error: {agent_id} ({agent_role}) "
                f"cannot validate {target_id} ({target_role}): {reason}"
            )
            super().__init__(message)

    class _MACIRoleNotAssignedErrorStub(_MACIErrorStub):
        error_code = "MACI_ROLE_NOT_ASSIGNED"

        def __init__(self, agent_id: str, action: str) -> None:
            self.agent_id = agent_id
            self.action = action
            message = f"Agent '{agent_id}' has no MACI role for: {action}"
            super().__init__(message)

    return (
        _MACIErrorStub,
        _MACIRoleViolationErrorStub,
        _MACISelfValidationErrorStub,
        _MACICrossRoleValidationErrorStub,
        _MACIRoleNotAssignedErrorStub,
    )


def _load_exception_classes() -> tuple[
    type[Exception],
    type[Exception],
    type[Exception],
    type[Exception],
    type[Exception],
]:
    try:
        from .exceptions import (
            MACICrossRoleValidationError as RelativeMACICrossRoleValidationError,
        )
        from .exceptions import (
            MACIError as RelativeMACIError,
        )
        from .exceptions import (
            MACIRoleNotAssignedError as RelativeMACIRoleNotAssignedError,
        )
        from .exceptions import (
            MACIRoleViolationError as RelativeMACIRoleViolationError,
        )
        from .exceptions import (
            MACISelfValidationError as RelativeMACISelfValidationError,
        )

        logger.debug("MACI exceptions loaded from relative import")
        return (
            RelativeMACIError,
            RelativeMACIRoleViolationError,
            RelativeMACISelfValidationError,
            RelativeMACICrossRoleValidationError,
            RelativeMACIRoleNotAssignedError,
        )
    except ImportError:
        logger.warning("MACI exceptions unavailable, creating stubs")
        return _build_exception_stubs()


(
    MACIError,
    MACIRoleViolationError,
    MACISelfValidationError,
    MACICrossRoleValidationError,
    MACIRoleNotAssignedError,
) = _load_exception_classes()

# =============================================================================
# Core MACI Imports (Models) - Lazy Loading
# =============================================================================

_model_cache: JSONDict = {}


def _load_models() -> bool:
    """Lazy-load MACI model classes into _model_cache."""
    global MACI_CORE_AVAILABLE, CONSTITUTIONAL_HASH  # noqa: PLW0603

    if _model_cache.get("_loaded"):
        return True

    try:
        from .core_models import get_enum_value as _get_enum_value
        from .models import AgentMessage as _AgentMessage
        from .models import MessageType as _MessageType

        _model_cache["AgentMessage"] = _AgentMessage
        _model_cache["MessageType"] = _MessageType
        _model_cache["get_enum_value"] = _get_enum_value
        _model_cache["_loaded"] = True

        MACI_CORE_AVAILABLE = True

        try:
            from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH as _hash

            CONSTITUTIONAL_HASH = _hash
        except ImportError:
            pass
        _model_cache["CONSTITUTIONAL_HASH"] = CONSTITUTIONAL_HASH

        logger.debug("MACI models loaded successfully")
        return True
    except ImportError as exc:
        logger.warning(f"MACI models unavailable: {exc}")
        return False


def get_agent_message() -> object:
    if not _model_cache.get("_loaded"):
        _load_models()
    return _model_cache.get("AgentMessage")


def get_message_type() -> object:
    if not _model_cache.get("_loaded"):
        _load_models()
    return _model_cache.get("MessageType")


def get_enum_value_func() -> Callable[..., object] | None:
    if not _model_cache.get("_loaded"):
        _load_models()
    value = _model_cache.get("get_enum_value")
    return value if callable(value) else None


_LAZY_MODEL_ATTRS = {"AgentMessage", "MessageType", "get_enum_value"}


def __getattr__(name: str) -> object:
    if name in _LAZY_MODEL_ATTRS:
        if not _model_cache.get("_loaded"):
            _load_models()
        value = _model_cache.get(name)
        if value is not None:
            globals()[name] = value
            return value
        raise AttributeError(f"MACI model {name!r} could not be loaded")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def ensure_maci_models_loaded() -> bool:
    result = _load_models()
    if result:
        for attr in _LAZY_MODEL_ATTRS:
            value = _model_cache.get(attr)
            if value is not None:
                globals()[attr] = value
    return result


def _load_get_iso_timestamp() -> Callable[[], str]:
    try:
        from enhanced_agent_bus.utils import get_iso_timestamp as package_get_iso_timestamp

        logger.debug("MACI utils loaded from enhanced_agent_bus import")

        def _wrapped_package_get_iso_timestamp() -> str:
            return str(package_get_iso_timestamp())

        return _wrapped_package_get_iso_timestamp
    except ImportError:
        try:
            from .utils import get_iso_timestamp as relative_get_iso_timestamp

            logger.debug("MACI utils loaded from relative import")

            def _wrapped_relative_get_iso_timestamp() -> str:
                return str(relative_get_iso_timestamp())

            return _wrapped_relative_get_iso_timestamp
        except ImportError:
            try:
                from utils import get_iso_timestamp as direct_get_iso_timestamp

                logger.debug("MACI utils loaded from direct import")
                def _wrapped_direct_get_iso_timestamp() -> str:
                    return str(direct_get_iso_timestamp())

                return _wrapped_direct_get_iso_timestamp
            except ImportError as exc:
                logger.debug(f"MACI utils unavailable, using fallback: {exc}")

                def _get_iso_timestamp_fallback() -> str:
                    return datetime.now(UTC).isoformat()

                return _get_iso_timestamp_fallback


get_iso_timestamp = _load_get_iso_timestamp()

__all__ = [
    "CONSTITUTIONAL_HASH",
    "GLOBAL_SETTINGS_AVAILABLE",
    "MACI_CORE_AVAILABLE",
    "OBSERVABILITY_AVAILABLE",
    "AgentMessage",
    "MACICrossRoleValidationError",
    "MACIError",
    "MACIRoleNotAssignedError",
    "MACIRoleViolationError",
    "MACISelfValidationError",
    "MessageType",
    "get_enum_value",  # lazy-loaded via __getattr__  # noqa: F822
    "get_iso_timestamp",
    "global_settings",
]
