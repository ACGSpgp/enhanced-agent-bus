"""
ACGS-2 Enhanced Agent Bus - Base Exceptions
Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

try:
    from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "standalone"
from enhanced_agent_bus._compat.errors import ACGSBaseError as _ACGSBaseError

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import JSONDict
else:
    try:
        from enhanced_agent_bus._compat.types import JSONDict
    except ImportError:
        JSONDict: TypeAlias = dict[str, Any]


class AgentBusError(_ACGSBaseError):
    """
    Base exception for all Enhanced Agent Bus errors.

    Inherits from ACGSBaseError to gain:
    - Constitutional hash tracking
    - Correlation ID for distributed tracing
    - Structured error details and logging
    - HTTP status code mapping
    - Timestamp for audit logging

    All custom exceptions in the agent bus inherit from this class,
    allowing for catch-all error handling when needed.
    """

    http_status_code = 500
    error_code = "AGENT_BUS_ERROR"

    def __init__(
        self,
        message: str,
        details: JSONDict | None = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        *,
        error_code: str | None = None,
        correlation_id: str | None = None,
        cause: BaseException | None = None,
        http_status_code: int | None = None,
        **kwargs: object,
    ) -> None:
        merged_details: JSONDict | None
        if details is None:
            merged_details = {}
        else:
            merged_details = dict(details)
        if kwargs:
            merged_details.update(kwargs)
        super().__init__(
            message,
            error_code=error_code,
            constitutional_hash=constitutional_hash,
            correlation_id=correlation_id,
            details=merged_details or None,
            cause=cause,
            http_status_code=http_status_code,
        )

    def to_dict(self) -> JSONDict:
        """
        Convert exception to dictionary for logging/serialization.

        Returns ACGSBaseError format (superset of old format):
        - Includes: error_code, message, constitutional_hash, correlation_id, timestamp, details
        - Compatible with old code expecting: error_type, message, details, constitutional_hash
        """
        result = super().to_dict()
        # Add legacy 'error_type' field for backward compatibility
        result["error_type"] = self.__class__.__name__
        return result


class ConstitutionalError(AgentBusError):
    """Base exception for constitutional compliance failures."""

    pass


class MessageError(AgentBusError):
    """Base exception for message-related errors."""

    pass


class AgentError(AgentBusError):
    """Base exception for agent-related errors."""

    pass


class PolicyError(AgentBusError):
    """Base exception for policy-related errors."""

    pass


class MACIError(AgentBusError):
    """Base exception for MACI role separation errors."""

    pass


class BusOperationError(AgentBusError):
    """Base exception for bus operation errors."""

    pass


__all__ = [
    "CONSTITUTIONAL_HASH",
    "AgentBusError",
    "AgentError",
    "BusOperationError",
    "ConstitutionalError",
    "MACIError",
    "MessageError",
    "PolicyError",
]
