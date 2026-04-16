"""Managed Agent executor integration for the Enhanced Agent Bus.

Routes AgentMessage objects through a GovernedManagedAgentsClient,
maintaining a session registry to reuse sessions across calls from
the same source agent.

CONSTITUTIONAL_HASH = "608508a9bd224290"
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from acgs_lite.integrations.anthropic_agents import GovernedManagedAgentsClient
    from acgs_lite.managed_agents import ManagedAgentConfig, ManagedAgentEvent, ManagedAgentSession

__all__ = ["EXECUTOR_TYPE", "ManagedAgentExecutor"]

logger = structlog.get_logger(__name__)

EXECUTOR_TYPE = "managed_agent"


class ManagedAgentExecutor:
    """Executor that routes AgentMessages through Anthropic Managed Agents.

    Maintains a session registry keyed by ``source_id`` so that messages
    from the same agent reuse an existing session rather than spinning up
    a new environment on every call.

    Args:
        client: Governed client for the Anthropic Managed Agents API.
        default_config: Config used when creating new sessions. Required if
            no session already exists for the source agent.
        session_registry: Pre-populated session registry (optional).
        poll_interval: Seconds to wait between polling for new events.
        poll_timeout: Maximum seconds to wait before raising TimeoutError.
    """

    executor_type: str = EXECUTOR_TYPE

    def __init__(
        self,
        client: GovernedManagedAgentsClient,
        default_config: ManagedAgentConfig | None = None,
        session_registry: dict[str, ManagedAgentSession] | None = None,
        poll_interval: float = 2.0,
        poll_timeout: int = 300,
    ) -> None:
        self.client = client
        self.default_config = default_config
        self._session_registry: dict[str, ManagedAgentSession] = session_registry or {}
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    async def execute(self, message: Any) -> Any:
        """Execute an AgentMessage via the Managed Agents API.

        Reuses an existing session if one is active for ``message.source_id``;
        otherwise creates a new session using ``default_config``.

        Args:
            message: AgentMessage-like object with ``content`` and ``source_id``.

        Returns:
            AgentMessage-like object with the assistant response in ``content``.

        Raises:
            RuntimeError: If no ``default_config`` and no existing session.
            asyncio.TimeoutError: If ``poll_timeout`` is exceeded.
        """
        source_id: str = getattr(message, "source_id", "default")
        content: str = getattr(message, "content", str(message))

        session = await self._get_or_create_session(source_id, task=content)

        self.client.send_event(session.session_id, content)
        logger.info(
            "managed_agent_executor.event_sent",
            session_id=session.session_id,
            source_id=source_id,
        )

        events = await self._poll_until_idle(session.session_id)
        return self._events_to_message(events, message)

    async def _get_or_create_session(self, agent_id: str, task: str) -> ManagedAgentSession:
        """Return the active session for *agent_id*, creating one if needed."""
        existing = self._session_registry.get(agent_id)
        if existing is not None and existing.status not in ("terminated", "error"):
            return existing

        if self.default_config is None:
            raise RuntimeError(
                f"No active session for agent_id={agent_id!r} and no default_config provided."
            )

        raw_agent = self.client.create_agent(self.default_config)
        raw_env = self.client.create_environment(name=f"env-{agent_id}")

        agent_sdk_id: str = (
            getattr(raw_agent, "id", None)
            or (raw_agent.get("id") if isinstance(raw_agent, dict) else None)
            or agent_id
        )
        env_sdk_id: str = (
            getattr(raw_env, "id", None)
            or (raw_env.get("id") if isinstance(raw_env, dict) else None)
            or "default-env"
        )

        raw_session = self.client.create_session(agent_sdk_id, env_sdk_id, task)

        from datetime import UTC, datetime

        from acgs_lite.managed_agents.models import ManagedAgentSession

        session_id: str = (
            getattr(raw_session, "id", None)
            or (raw_session.get("id") if isinstance(raw_session, dict) else None)
            or "unknown"
        )
        session = ManagedAgentSession(
            session_id=session_id,
            agent_id=agent_sdk_id,
            environment_id=env_sdk_id,
            status="running",
            created_at=datetime.now(tz=UTC),
            task=task,
        )
        self._session_registry[agent_id] = session
        logger.info(
            "managed_agent_executor.session_created",
            session_id=session_id,
            agent_id=agent_id,
        )
        return session

    async def _poll_until_idle(
        self,
        session_id: str,
        timeout: int | None = None,
        poll_interval: float | None = None,
    ) -> list[ManagedAgentEvent]:
        """Poll *session_id* until it reaches a terminal status.

        Args:
            session_id: Session to monitor.
            timeout: Override for ``poll_timeout`` (seconds).
            poll_interval: Override for ``poll_interval`` (seconds).

        Returns:
            All events collected during polling.

        Raises:
            asyncio.TimeoutError: If the deadline is exceeded.
        """
        effective_timeout = timeout if timeout is not None else self.poll_timeout
        effective_interval = poll_interval if poll_interval is not None else self.poll_interval

        loop = asyncio.get_running_loop()
        deadline = loop.time() + effective_timeout
        all_events: list[ManagedAgentEvent] = []
        last_event_id: str | None = None

        while True:
            if loop.time() > deadline:
                raise TimeoutError(
                    f"Poll timeout ({effective_timeout}s) exceeded for session {session_id}"
                )

            events = self.client.poll_events(session_id, after=last_event_id)
            if events:
                all_events.extend(events)
                last_event_id = events[-1].event_id

            raw_session = self.client.get_session(session_id)
            status: str = (
                getattr(raw_session, "status", None)
                or (raw_session.get("status") if isinstance(raw_session, dict) else None)
                or "running"
            )
            if status in ("idle", "terminated", "error"):
                # Update registry with the terminal status
                for key, sess in self._session_registry.items():
                    if sess.session_id == session_id:
                        self._session_registry[key] = sess.model_copy(update={"status": status})
                        break
                break

            await asyncio.sleep(effective_interval)

        return all_events

    def _events_to_message(self, events: list[ManagedAgentEvent], source: Any) -> Any:
        """Collapse *events* into a single response message.

        Args:
            events: Events collected from the session.
            source: Original incoming message (used to construct the reply).

        Returns:
            A message object of the same type as *source*, or a plain dict
            if the source constructor is incompatible.
        """
        from acgs_lite.managed_agents.events import ManagedAgentEventType

        assistant_parts = [
            e.content if isinstance(e.content, str) else str(e.content)
            for e in events
            if e.event_type == ManagedAgentEventType.ASSISTANT_MESSAGE
        ]
        response_content = "\n".join(assistant_parts) if assistant_parts else ""

        try:
            return source.__class__(
                content=response_content,
                source_id=getattr(source, "target_id", "managed-agent"),
                target_id=getattr(source, "source_id", "caller"),
                metadata={
                    "event_count": len(events),
                    "executor_type": self.executor_type,
                    **(getattr(source, "metadata", None) or {}),
                },
            )
        except Exception:
            return {
                "content": response_content,
                "source_id": "managed-agent",
                "metadata": {"event_count": len(events), "executor_type": self.executor_type},
            }
