"""
ACGS-2 Enhanced Agent Bus - Performance Optimization Extension Exports
Constitutional Hash: 608508a9bd224290

Extension module for Phase 6: Performance Optimization.
Provides clean import interface with graceful fallback when the
performance_optimization module is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

        PERFORMANCE_OPTIMIZATION_AVAILABLE = False

        # Task 6.1 stubs
        PipelineStage = object
        PipelineResult = object
        AsyncPipelineOptimizer = object
        create_async_pipeline: Any = None

        # Task 6.2 stubs
        PooledResource = object
        ResourceFactory = object
        ResourcePool = object
        create_resource_pool: Any = None

        # Task 6.3 stubs
        PerformanceCacheEntry = object
        MemoryOptimizer = object
        create_memory_optimizer: Any = None

        # Task 6.4 stubs
        BatchConfig = object
        BatchFlushResult = object
        BatchProcessor = object
        LatencyReducer = object
        create_latency_reducer: Any = None

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

_EXT_ALL = __all__
