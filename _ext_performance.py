"""
ACGS-2 Enhanced Agent Bus - Performance Optimization Extension Exports
Constitutional Hash: 608508a9bd224290

Extension module for Phase 6: Performance Optimization.
Provides clean import interface with graceful fallback when the
performance_optimization module is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "PERFORMANCE_OPTIMIZATION_AVAILABLE",
    "AsyncPipelineOptimizer",
    # Task 6.4: Latency Reducer
    "BatchConfig",
    "BatchFlushResult",
    "BatchProcessor",
    "LatencyReducer",
    "MemoryOptimizer",
    # Task 6.3: Memory Optimizer
    "PerformanceCacheEntry",
    "PipelineResult",
    # Task 6.1: Async Pipeline Optimizer
    "PipelineStage",
    # Task 6.2: Resource Pool
    "PooledResource",
    "ResourceFactory",
    "ResourcePool",
    "create_async_pipeline",
    "create_latency_reducer",
    "create_memory_optimizer",
    "create_resource_pool",
]

_FALLBACK_EXPORTS: dict[str, Any] = {
    "PERFORMANCE_OPTIMIZATION_AVAILABLE": False,
    "create_async_pipeline": None,
    "create_resource_pool": None,
    "create_memory_optimizer": None,
    "create_latency_reducer": None,
}

if TYPE_CHECKING:
    from .performance_optimization import (
        PERFORMANCE_OPTIMIZATION_AVAILABLE,
        AsyncPipelineOptimizer,
        BatchConfig,
        BatchFlushResult,
        BatchProcessor,
        LatencyReducer,
        MemoryOptimizer,
        PipelineResult,
        PipelineStage,
        PooledResource,
        ResourceFactory,
        ResourcePool,
        create_async_pipeline,
        create_latency_reducer,
        create_memory_optimizer,
        create_resource_pool,
    )
    from .performance_optimization import (
        CacheEntry as PerformanceCacheEntry,
    )
else:
    try:
        from .performance_optimization import (
            # Feature flag
            PERFORMANCE_OPTIMIZATION_AVAILABLE,
            # Task 6.1: Async Pipeline Optimizer
            AsyncPipelineOptimizer,
            BatchConfig,
            # Task 6.4: Latency Reducer
            BatchFlushResult,
            BatchProcessor,
            # Factory functions
            LatencyReducer,
            MemoryOptimizer,
            PipelineResult,
            # Task 6.1
            PipelineStage,
            PooledResource,
            # Task 6.2: Resource Pool
            ResourceFactory,
            ResourcePool,
            create_async_pipeline,
            create_latency_reducer,
            create_memory_optimizer,
            create_resource_pool,
        )
        from .performance_optimization import (
            # Task 6.3: Memory Optimizer
            CacheEntry as PerformanceCacheEntry,
        )
    except ImportError:
        # Graceful fallback if performance optimization module is not available

        for name in __all__:
            globals()[name] = _FALLBACK_EXPORTS.get(name, object)

_EXT_ALL = __all__
