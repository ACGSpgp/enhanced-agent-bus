# Constitutional Hash: 608508a9bd224290
""" 
Optional circuit breaker imports for enhanced_agent_bus.
Service-Specific Circuit Breaker Configuration (T002).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .circuit_breaker import (
        SERVICE_CIRCUIT_CONFIGS,
        CircuitBreakerMetrics,
        CircuitBreakerOpen,
        CircuitState,
        FallbackStrategy,
        QueuedRequest,
        ServiceCircuitBreaker,
        ServiceCircuitBreakerRegistry,
        ServiceCircuitConfig,
        ServiceSeverity,
        create_circuit_health_router,
        get_circuit_breaker_registry,
        get_service_circuit_breaker,
        get_service_config,
        reset_circuit_breaker_registry,
        with_service_circuit_breaker,
    )
else:
    try:
        from .circuit_breaker import (
            SERVICE_CIRCUIT_CONFIGS,
            CircuitBreakerMetrics,
            CircuitBreakerOpen,
            CircuitState,
            FallbackStrategy,
            QueuedRequest,
            ServiceCircuitBreaker,
            ServiceCircuitBreakerRegistry,
            ServiceCircuitConfig,
            ServiceSeverity,
            create_circuit_health_router,
            get_circuit_breaker_registry,
            get_service_circuit_breaker,
            get_service_config,
            reset_circuit_breaker_registry,
            with_service_circuit_breaker,
        )

        SERVICE_CIRCUIT_BREAKER_AVAILABLE = True
    except ImportError:
        SERVICE_CIRCUIT_BREAKER_AVAILABLE = False
        CircuitBreakerMetrics = object
        CircuitBreakerOpen = object
        CircuitState = object
        FallbackStrategy = object
        QueuedRequest = object
        SERVICE_CIRCUIT_CONFIGS = {}
        ServiceCircuitBreaker = object
        ServiceCircuitBreakerRegistry = object
        ServiceCircuitConfig = object
        ServiceSeverity = object
        create_circuit_health_router = object
        get_circuit_breaker_registry = object
        get_service_circuit_breaker = object
        get_service_config = object
        reset_circuit_breaker_registry = object
        with_service_circuit_breaker = object

_EXT_ALL = [
    "SERVICE_CIRCUIT_BREAKER_AVAILABLE",
    "SERVICE_CIRCUIT_CONFIGS",
    "ServiceCircuitConfig",
    "ServiceCircuitBreaker",
    "ServiceCircuitBreakerRegistry",
    "ServiceSeverity",
    "FallbackStrategy",
    "CircuitState",
    "CircuitBreakerOpen",
    "CircuitBreakerMetrics",
    "QueuedRequest",
    "get_service_config",
    "get_service_circuit_breaker",
    "get_circuit_breaker_registry",
    "reset_circuit_breaker_registry",
    "with_service_circuit_breaker",
    "create_circuit_health_router",
]
