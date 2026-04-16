"""Tests for ManagedAgentExecutor (Unit 4).

All Anthropic SDK calls are mocked.  No live API calls are made.

CONSTITUTIONAL_HASH = "608508a9bd224290"
"""

from __future__ import annotations

import asyncio
import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub anthropic and acgs_lite.managed_agents before importing the executor.
# The managed_agents subpackage is only present in the feature worktree; the
# main-repo acgs_lite installation may not have it yet.  We stub it so that
# this test file runs without needing the worktree on the Python path.
# ---------------------------------------------------------------------------

_anthropic_stub = types.ModuleType("anthropic")
_anthropic_stub.Anthropic = MagicMock
sys.modules.setdefault("anthropic", _anthropic_stub)
sys.modules["anthropic"] = _anthropic_stub

# ---- managed_agents stub ----
_ma_pkg = types.ModuleType("acgs_lite.managed_agents")
_ma_events = types.ModuleType("acgs_lite.managed_agents.events")
_ma_models = types.ModuleType("acgs_lite.managed_agents.models")

# Try to import the real modules first (available when running from worktree)
try:
    from acgs_lite.managed_agents.events import (  # type: ignore[import]
        ManagedAgentEvent,
        ManagedAgentEventType,
    )
    from acgs_lite.managed_agents.models import (  # type: ignore[import]
        ManagedAgentConfig,
        ManagedAgentSession,
    )
except ModuleNotFoundError:
    # Build minimal Pydantic-free stand-ins so the executor tests run in CI
    # against the main-repo acgs_lite installation.
    from datetime import UTC, datetime
    from enum import StrEnum
    from typing import Any

    from pydantic import BaseModel, Field

    class ManagedAgentEventType(StrEnum):  # type: ignore[no-redef]
        USER_MESSAGE = "user_message"
        ASSISTANT_MESSAGE = "assistant_message"
        TOOL_USE = "tool_use"
        TOOL_RESULT = "tool_result"
        STATUS = "session_status"
        ERROR = "error"

    class ManagedAgentEvent(BaseModel):  # type: ignore[no-redef]
        event_id: str
        session_id: str
        event_type: ManagedAgentEventType
        content: str | dict
        timestamp: datetime
        metadata: dict = Field(default_factory=dict)

        model_config = {"frozen": True}

    class ManagedAgentConfig(BaseModel):  # type: ignore[no-redef]
        name: str
        model: str = "claude-sonnet-4-6"
        system_prompt: str
        tools: list = Field(default_factory=list)
        mcp_servers: list = Field(default_factory=list)
        max_tokens: int = 8192

    class ManagedAgentSession(BaseModel):  # type: ignore[no-redef]
        session_id: str
        agent_id: str
        environment_id: str
        status: str
        created_at: datetime
        task: str

    _ma_events.ManagedAgentEvent = ManagedAgentEvent
    _ma_events.ManagedAgentEventType = ManagedAgentEventType
    _ma_models.ManagedAgentConfig = ManagedAgentConfig
    _ma_models.ManagedAgentSession = ManagedAgentSession
    sys.modules.setdefault("acgs_lite.managed_agents", _ma_pkg)
    sys.modules.setdefault("acgs_lite.managed_agents.events", _ma_events)
    sys.modules.setdefault("acgs_lite.managed_agents.models", _ma_models)

from enhanced_agent_bus.integrations.managed_agent_executor import (  # noqa: E402
    EXECUTOR_TYPE,
    ManagedAgentExecutor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 11, 0, 0, 0, tzinfo=UTC)


def _evt(
    event_id: str = "e1",
    session_id: str = "s1",
    event_type: ManagedAgentEventType = ManagedAgentEventType.ASSISTANT_MESSAGE,
    content: str = "Done.",
) -> ManagedAgentEvent:
    return ManagedAgentEvent(
        event_id=event_id,
        session_id=session_id,
        event_type=event_type,
        content=content,
        timestamp=_NOW,
    )


def _make_session(
    session_id: str = "s1",
    agent_id: str = "a1",
    env_id: str = "env1",
    status: str = "running",
    task: str = "default task",
) -> ManagedAgentSession:
    return ManagedAgentSession(
        session_id=session_id,
        agent_id=agent_id,
        environment_id=env_id,
        status=status,  # type: ignore[arg-type]
        created_at=_NOW,
        task=task,
    )


def _stub_client(
    events: list[ManagedAgentEvent] | None = None,
    session_status: str = "idle",
) -> MagicMock:
    """Return a mock GovernedManagedAgentsClient (no spec — avoids the worktree import)."""
    client = MagicMock()
    client.create_agent.return_value = SimpleNamespace(id="a1")
    client.create_environment.return_value = SimpleNamespace(id="env1")
    client.create_session.return_value = SimpleNamespace(id="s1", status="running")
    client.get_session.return_value = SimpleNamespace(id="s1", status=session_status)
    client.poll_events.return_value = events or []
    client.send_event.return_value = None
    return client


class _Msg:
    """Minimal AgentMessage stand-in."""

    def __init__(
        self,
        content: str = "hello",
        source_id: str = "caller",
        target_id: str = "managed-agent",
        metadata: dict | None = None,
    ) -> None:
        self.content = content
        self.source_id = source_id
        self.target_id = target_id
        self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# EXECUTOR_TYPE constant
# ---------------------------------------------------------------------------


def test_executor_type_constant() -> None:
    assert EXECUTOR_TYPE == "managed_agent"
    assert ManagedAgentExecutor.executor_type == "managed_agent"


# ---------------------------------------------------------------------------
# _get_or_create_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_creates_new_session() -> None:
    client = _stub_client()
    cfg = ManagedAgentConfig(name="bot", system_prompt="Help.")
    executor = ManagedAgentExecutor(client=client, default_config=cfg)

    session = await executor._get_or_create_session("agent-x", "my task")
    assert session.session_id == "s1"
    assert "agent-x" in executor._session_registry


@pytest.mark.asyncio
async def test_get_or_create_reuses_running_session() -> None:
    client = _stub_client()
    existing = _make_session(session_id="existing-sess", status="running")
    executor = ManagedAgentExecutor(
        client=client,
        session_registry={"agent-x": existing},
    )

    session = await executor._get_or_create_session("agent-x", "any task")
    assert session.session_id == "existing-sess"
    client.create_agent.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_replaces_terminated_session() -> None:
    client = _stub_client()
    cfg = ManagedAgentConfig(name="bot", system_prompt="Help.")
    dead = _make_session(session_id="dead-sess", status="terminated")
    executor = ManagedAgentExecutor(
        client=client,
        default_config=cfg,
        session_registry={"agent-x": dead},
    )

    session = await executor._get_or_create_session("agent-x", "new task")
    assert session.session_id == "s1"  # new session from stub
    client.create_agent.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_raises_without_config_and_no_session() -> None:
    client = _stub_client()
    executor = ManagedAgentExecutor(client=client, default_config=None)

    with pytest.raises(RuntimeError, match="no default_config"):
        await executor._get_or_create_session("agent-y", "task")


# ---------------------------------------------------------------------------
# _poll_until_idle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_poll_until_idle_returns_events() -> None:
    events = [_evt(content="Step 1."), _evt(event_id="e2", content="Step 2.")]
    client = _stub_client(events=events, session_status="idle")
    executor = ManagedAgentExecutor(client=client, poll_interval=0.0)

    # Register a session so we can test registry update
    session = _make_session(session_id="s1")
    executor._session_registry["agent-x"] = session

    collected = await executor._poll_until_idle("s1")
    assert len(collected) == 2
    assert collected[0].content == "Step 1."


@pytest.mark.asyncio
async def test_poll_until_idle_raises_on_timeout() -> None:
    client = _stub_client(session_status="running")
    executor = ManagedAgentExecutor(client=client, poll_timeout=0, poll_interval=0.0)

    with pytest.raises(TimeoutError):
        await executor._poll_until_idle("s1", timeout=0)


@pytest.mark.asyncio
async def test_poll_until_idle_updates_registry_status() -> None:
    client = _stub_client(session_status="terminated")
    cfg = ManagedAgentConfig(name="b", system_prompt="p")
    executor = ManagedAgentExecutor(client=client, default_config=cfg, poll_interval=0.0)
    executor._session_registry["agent-x"] = _make_session(session_id="s1")

    await executor._poll_until_idle("s1")

    updated = executor._session_registry["agent-x"]
    assert updated.status == "terminated"


# ---------------------------------------------------------------------------
# _events_to_message
# ---------------------------------------------------------------------------


def test_events_to_message_collapses_assistant_messages() -> None:
    client = _stub_client()
    executor = ManagedAgentExecutor(client=client)

    events = [
        _evt(event_id="e1", content="Part 1."),
        _evt(event_id="e2", content="Part 2."),
    ]
    source = _Msg(content="query", source_id="caller", target_id="managed-agent")
    result = executor._events_to_message(events, source)

    assert "Part 1." in result.content
    assert "Part 2." in result.content


def test_events_to_message_ignores_non_assistant_events() -> None:
    client = _stub_client()
    executor = ManagedAgentExecutor(client=client)

    events = [
        _evt(event_id="e1", event_type=ManagedAgentEventType.STATUS, content="status"),
        _evt(event_id="e2", content="Final answer."),
    ]
    source = _Msg()
    result = executor._events_to_message(events, source)

    assert "Final answer." in result.content
    assert "status" not in result.content


def test_events_to_message_empty_produces_empty_content() -> None:
    client = _stub_client()
    executor = ManagedAgentExecutor(client=client)

    source = _Msg()
    result = executor._events_to_message([], source)
    assert result.content == "" or result["content"] == ""  # type: ignore[index]


def test_events_to_message_falls_back_to_dict_on_incompatible_class() -> None:
    """If source.__class__() raises, result is a plain dict."""

    class Incompatible:
        def __init__(self) -> None:
            pass  # no keyword args

    client = _stub_client()
    executor = ManagedAgentExecutor(client=client)

    result = executor._events_to_message([_evt()], Incompatible())
    assert isinstance(result, dict)
    assert "content" in result
    assert result["metadata"]["executor_type"] == "managed_agent"


# ---------------------------------------------------------------------------
# execute() — end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_creates_session_and_returns_response() -> None:
    events = [_evt(content="Summary complete.")]
    client = _stub_client(events=events, session_status="idle")
    cfg = ManagedAgentConfig(name="bot", system_prompt="Summarise.")
    executor = ManagedAgentExecutor(client=client, default_config=cfg, poll_interval=0.0)

    msg = _Msg(content="Summarise this doc.", source_id="caller")
    result = await executor.execute(msg)

    client.send_event.assert_called_once()
    assert "Summary complete." in result.content


@pytest.mark.asyncio
async def test_execute_reuses_existing_session() -> None:
    events = [_evt()]
    client = _stub_client(events=events, session_status="idle")
    existing = _make_session(session_id="existing", status="running")
    executor = ManagedAgentExecutor(
        client=client,
        session_registry={"caller": existing},
        poll_interval=0.0,
    )

    msg = _Msg(source_id="caller", content="Follow-up question.")
    await executor.execute(msg)

    # Agent and env should NOT be created again
    client.create_agent.assert_not_called()
    client.send_event.assert_called_once_with("existing", "Follow-up question.")
