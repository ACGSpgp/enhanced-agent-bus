"""
ACGS-2 Enhanced Agent Bus - Registry Implementations
Constitutional Hash: 608508a9bd224290
"""

import asyncio
import json
import sys
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, cast

from enhanced_agent_bus.observability.structured_logging import get_logger

if TYPE_CHECKING:
    import redis.asyncio as redis_async

from enhanced_agent_bus.bus_types import JSONDict, JSONValue, MetadataDict

if TYPE_CHECKING:
    from enhanced_agent_bus._compat.types import AgentInfo
else:
    AgentInfo: TypeAlias = JSONDict

from .interfaces import (
    AgentRegistry,
    MessageRouter,
    ProcessingStrategy,
    ValidationStrategy,
)
from .models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus

# Import validation and processing strategies from extracted modules
from .processing_strategies import (
    CompositeProcessingStrategy,
    DynamicPolicyProcessingStrategy,
    MACIProcessingStrategy,
    OPAProcessingStrategy,
    PythonProcessingStrategy,
    RustProcessingStrategy,
)
from .validation_strategies import (
    CompositeValidationStrategy,
    DynamicPolicyValidationStrategy,
    OPAValidationStrategy,
    PQCValidationStrategy,
    RustValidationStrategy,
    StaticHashValidationStrategy,
)
from .validators import ValidationResult

logger = get_logger(__name__)
sys.modules.setdefault("registry", sys.modules[__name__])
sys.modules.setdefault("enhanced_agent_bus.registry", sys.modules[__name__])
sys.modules.setdefault("packages.enhanced_agent_bus.registry", sys.modules[__name__])
# Redis connection pool defaults to prevent resource exhaustion
DEFAULT_REDIS_MAX_CONNECTIONS = 20
DEFAULT_REDIS_SOCKET_TIMEOUT = 5.0
DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT = 5.0


class _RedisRegistryPoolProtocol(Protocol):
    async def disconnect(self) -> object: ...


class _RedisRegistryClientProtocol(Protocol):
    async def hsetnx(self, name: str, key: str, value: str) -> int: ...
    async def hdel(self, name: str, key: str) -> int: ...
    async def hget(self, name: str, key: str) -> str | None: ...
    async def hkeys(self, name: str) -> list[str]: ...
    async def hexists(self, name: str, key: str) -> bool: ...
    async def hset(self, name: str, key: str, value: str) -> int: ...
    async def delete(self, key: str) -> int: ...
    async def close(self) -> object: ...


class InMemoryAgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def register(
        self,
        agent_id: str,
        capabilities: list[str] | None = None,
        metadata: MetadataDict | None = None,
    ) -> bool:
        if agent_id in self._agents:
            return False
        safe_metadata: MetadataDict = metadata or {}
        self._agents[agent_id] = cast(
            AgentInfo,
            {
                "agent_id": agent_id,
                "capabilities": capabilities or [],
                "metadata": safe_metadata,
                "registered_at": datetime.now(UTC).isoformat(),
                "constitutional_hash": self._constitutional_hash,
            },
        )
        return True

    async def unregister(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        return True

    async def get(self, agent_id: str) -> AgentInfo | None:
        return self._agents.get(agent_id)

    async def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def exists(self, agent_id: str) -> bool:
        return agent_id in self._agents

    async def update_metadata(self, agent_id: str, metadata: MetadataDict) -> bool:
        if agent_id not in self._agents:
            return False
        agent_metadata = cast(MetadataDict, self._agents[agent_id]["metadata"])
        agent_metadata.update(metadata)
        self._agents[agent_id]["updated_at"] = datetime.now(UTC).isoformat()
        return True

    async def clear(self) -> None:
        self._agents.clear()

    @property
    def agent_count(self) -> int:
        return len(self._agents)


class RedisAgentRegistry:
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "acgs2:registry:agents",
        max_connections: int = DEFAULT_REDIS_MAX_CONNECTIONS,
        socket_timeout: float = DEFAULT_REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout: float = DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT,
    ) -> None:
        self._redis_url, self._key_prefix, self._max_connections = (
            redis_url,
            key_prefix,
            max_connections,
        )
        self._socket_timeout, self._socket_connect_timeout = socket_timeout, socket_connect_timeout
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._redis: _RedisRegistryClientProtocol | None = None
        self._pool: _RedisRegistryPoolProtocol | None = None

    async def _get_client(self) -> _RedisRegistryClientProtocol:
        try:
            import redis.asyncio as redis
        except ImportError as e:
            raise ImportError("RedisAgentRegistry requires 'redis' package.") from e
        if self._redis is None:
            self._pool = redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                decode_responses=True,
            )
            self._redis = cast(
                _RedisRegistryClientProtocol, redis.Redis(connection_pool=self._pool)
            )
        return self._redis

    async def register(
        self, aid: str, caps: list[str] | None = None, meta: MetadataDict | None = None
    ) -> bool:
        client = await self._get_client()
        info = {
            "agent_id": aid,
            "capabilities": caps or {},
            "metadata": meta or {},
            "registered_at": datetime.now(UTC).isoformat(),
            "constitutional_hash": self._constitutional_hash,
        }
        return bool(await client.hsetnx(self._key_prefix, aid, json.dumps(info)))

    async def unregister(self, aid: str) -> bool:
        client = await self._get_client()
        return bool(await client.hdel(self._key_prefix, aid) > 0)

    async def get(self, aid: str) -> AgentInfo | None:
        client = await self._get_client()
        data = await client.hget(self._key_prefix, aid)
        return json.loads(data) if data else None

    async def list_agents(self) -> list[str]:
        client = await self._get_client()
        return list(await client.hkeys(self._key_prefix))

    async def exists(self, aid: str) -> bool:
        client = await self._get_client()
        return bool(await client.hexists(self._key_prefix, aid))

    async def update_metadata(self, aid: str, meta: MetadataDict) -> bool:
        client = await self._get_client()
        data = await client.hget(self._key_prefix, aid)
        if not data:
            return False
        info = cast(dict[str, Any], json.loads(data))
        info["metadata"].update(meta)
        info["updated_at"] = datetime.now(UTC).isoformat()
        await client.hset(self._key_prefix, aid, json.dumps(info))
        return True

    async def clear(self) -> None:
        client = await self._get_client()
        await client.delete(self._key_prefix)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def agent_count(self) -> int:
        return -1


class DirectMessageRouter:
    def __init__(self) -> None:
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(self, msg: AgentMessage, reg: AgentRegistry) -> str | None:
        target = msg.to_agent
        if not target:
            return None
        info = await reg.get(target)
        if not info:
            return None
        msg_t = msg.tenant_id or None
        metadata = info.get("metadata", {})
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        agent_t = (info.get("tenant_id") or metadata_dict.get("tenant_id")) or None
        if msg_t != agent_t:
            logger.warning(f"Tenant mismatch: {msg_t} vs {agent_t}")
            return None
        return cast(str | None, target)

    async def broadcast(
        self, msg: AgentMessage, reg: AgentRegistry, exclude: list[str] | None = None
    ) -> list[str]:
        all_a, ex = await reg.list_agents(), set(exclude or [])
        if msg.from_agent:
            ex.add(msg.from_agent)
        return [a for a in all_a if a not in ex]


class CapabilityBasedRouter:
    def __init__(self) -> None:
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(self, msg: AgentMessage, reg: AgentRegistry) -> str | None:
        target = msg.to_agent
        if isinstance(target, str) and await reg.exists(target):
            return target
        req = msg.content.get("required_capabilities", []) if isinstance(msg.content, dict) else []
        if not req:
            return None
        for aid in await reg.list_agents():
            info = await reg.get(aid)
            capabilities: object = info.get("capabilities", {}) if info else {}
            capability_set: list[object] | dict[object, object] = (
                capabilities if isinstance(capabilities, (dict, list)) else {}
            )
            if info and all(c in capability_set for c in req):
                return str(aid)
        return None

    async def broadcast(
        self, msg: AgentMessage, reg: AgentRegistry, exclude: list[str] | None = None
    ) -> list[str]:
        req, ex = (
            (msg.content.get("required_capabilities", []) if isinstance(msg.content, dict) else []),
            set(exclude or []),
        )
        if msg.from_agent:
            ex.add(msg.from_agent)
        res = []
        for aid in await reg.list_agents():
            if aid in ex:
                continue
            info = await reg.get(aid)
            if info and (not req or all(c in info.get("capabilities", {}) for c in req)):
                res.append(aid)
        return res


__all__ = [
    "CapabilityBasedRouter",
    "CompositeProcessingStrategy",
    "CompositeValidationStrategy",
    "DirectMessageRouter",
    "DynamicPolicyProcessingStrategy",
    "DynamicPolicyValidationStrategy",
    "InMemoryAgentRegistry",
    "MACIProcessingStrategy",
    "OPAProcessingStrategy",
    "OPAValidationStrategy",
    "PQCValidationStrategy",
    "PythonProcessingStrategy",
    "RedisAgentRegistry",
    "RustProcessingStrategy",
    "RustValidationStrategy",
    "StaticHashValidationStrategy",
]
