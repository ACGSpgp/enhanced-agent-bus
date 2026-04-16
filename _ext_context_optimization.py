"""
ACGS-2 Enhanced Agent Bus - Context Optimization Extension Exports
Constitutional Hash: 608508a9bd224290

Extension module for Phase 4: Context Window Optimization.
Provides clean import interface for context optimization components.
"""

from typing import Any

__all__ = [
    "CONTEXT_OPTIMIZATION_AVAILABLE",
    "CachedGovernanceValidator",
    "CompressionResult",
    # Task 4.1
    "CompressionStrategy",
    # Task 4.2
    "GovernanceDecision",
    "GovernanceValidatorProtocol",
    "OptimizedAgentBus",
    "PartitionBroker",
    "PartitionedMessage",
    "SpecBaseline",
    "SpecDeltaCompressor",
    "TopicConfig",
    # Task 4.3
    "TopicPriority",
    "ValidationContext",
    "create_cached_validator",
    "create_optimized_bus",
    "create_spec_compressor",
]

_FALLBACK_EXPORTS: dict[str, Any] = {
    "CONTEXT_OPTIMIZATION_AVAILABLE": False,
    "create_spec_compressor": None,
    "create_cached_validator": None,
    "create_optimized_bus": None,
}

try:
    from .context_optimization import (
        # Feature flag
        CONTEXT_OPTIMIZATION_AVAILABLE,
        CachedGovernanceValidator,
        CompressionResult,
        # Task 4.1: Spec Delta Compression
        CompressionStrategy,
        # Task 4.2: Cached Governance Validator
        GovernanceDecision,
        GovernanceValidatorProtocol,
        OptimizedAgentBus,
        PartitionBroker,
        PartitionedMessage,
        SpecBaseline,
        SpecDeltaCompressor,
        TopicConfig,
        # Task 4.3: Optimized Agent Bus
        TopicPriority,
        ValidationContext,
        create_cached_validator,
        create_optimized_bus,
        create_spec_compressor,
    )
except ImportError:
    # Graceful fallback if context optimization not available

    for name in __all__:
        globals()[name] = _FALLBACK_EXPORTS.get(name, object)

_EXT_ALL = __all__
