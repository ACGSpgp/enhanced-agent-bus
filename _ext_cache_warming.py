# Constitutional Hash: 608508a9bd224290
"""Optional cache warming integration for FastAPI startup."""

from typing import Any

try:
    from enhanced_agent_bus._compat.cache_warming import (
        CacheWarmer,
        WarmingConfig,
        WarmingProgress,
        WarmingResult,
        WarmingStatus,
        get_cache_warmer,
        reset_cache_warmer,
        warm_cache_on_startup,
    )

    CACHE_WARMING_AVAILABLE = True
except ImportError:
    CACHE_WARMING_AVAILABLE = False
    CacheWarmer = Any
    WarmingConfig = Any
    WarmingProgress = Any
    WarmingResult = Any
    WarmingStatus = Any
    get_cache_warmer = Any
    reset_cache_warmer = Any
    warm_cache_on_startup = Any

_EXT_ALL = [
    "CACHE_WARMING_AVAILABLE",
    "CacheWarmer",
    "WarmingConfig",
    "WarmingProgress",
    "WarmingResult",
    "WarmingStatus",
    "get_cache_warmer",
    "reset_cache_warmer",
    "warm_cache_on_startup",
]
