"""Stable compat shim for audit enums and logger access."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class AuditEventType(StrEnum):
    """Union of legacy and MCP-facing audit event types used in this repo."""

    APPROVAL = "approval"
    VALIDATION = "validation"
    DECISION = "decision"
    SYSTEM = "system"
    PRINCIPLE_ACCESS = "principle_access"
    PRECEDENT_QUERY = "precedent_query"
    ESCALATION = "escalation"
    APPEAL = "appeal"


class AuditSeverity(StrEnum):
    """Compat severity enum matching shared audit logging values."""

    INFO = "info"
    WARNING = "warning"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogger:
    """No-op audit logger shim."""

    def __init__(self, **kwargs: Any) -> None:
        del kwargs

    async def log(
        self,
        event_type: str = "",
        severity: str = "info",
        message: str = "",
        **kwargs: Any,
    ) -> None:
        del event_type, severity, message, kwargs

    async def query(self, **filters: Any) -> list[dict[str, Any]]:
        del filters
        return []


def get_audit_logger(**kwargs: Any) -> AuditLogger:
    return AuditLogger(**kwargs)


__all__ = [
    "AuditEventType",
    "AuditLogger",
    "AuditSeverity",
    "get_audit_logger",
]
