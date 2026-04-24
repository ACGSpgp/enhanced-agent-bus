"""Central registry for optional module availability checks."""

from __future__ import annotations

from importlib.util import find_spec


class PluginNotAvailable(ImportError):
    """Raised when an optional plugin module is unavailable."""

    def __init__(self, name: str, module_path: str, install_hint: str | None = None) -> None:
        message = f"Plugin '{name}' is not available ({module_path})"
        if install_hint:
            message = f"{message}. Install with: pip install {install_hint}"
        super().__init__(message)
        self.name = name
        self.module_path = module_path
        self.install_hint = install_hint


PLUGINS: dict[str, str] = {
    "ab_testing": "enhanced_agent_bus.ab_testing",
    "anomaly_monitoring": "src.core.integrations.anomaly_monitoring",
    "dfc_metrics": "src.core.shared.governance.metrics.dfc",
    "drift_monitoring": "drift_monitoring",
    "feedback_handler": "enhanced_agent_bus.feedback_handler",
    "governance_mhc": "enhanced_agent_bus.governance.stability.mhc",
    "hotl_manager": "src.core.services.hitl_approvals.hotl_manager",
    "maci_enforcement": "enhanced_agent_bus.maci_enforcement",
    "maci_strategy": "enhanced_agent_bus.maci.strategy",
    "mlflow": "mlflow",
    "numpy": "numpy",
    "online_learning": "enhanced_agent_bus.online_learning",
    "opa_guard_mixin": "enhanced_agent_bus.deliberation_layer.opa_guard_mixin",
    "pandas": "pandas",
    "sklearn": "sklearn.ensemble",
    "z3": "z3",
    # Optional _ext_* extension modules (US-006).
    "_ext_browser_tool": "enhanced_agent_bus._ext_browser_tool",
    "_ext_cache_warming": "enhanced_agent_bus._ext_cache_warming",
    "_ext_chaos": "enhanced_agent_bus._ext_chaos",
    "_ext_circuit_breaker": "enhanced_agent_bus._ext_circuit_breaker",
    "_ext_circuit_breaker_clients": "enhanced_agent_bus._ext_circuit_breaker_clients",
    "_ext_cognee": "enhanced_agent_bus._ext_cognee",
    "_ext_cognitive": "enhanced_agent_bus._ext_cognitive",
    "_ext_context_memory": "enhanced_agent_bus._ext_context_memory",
    "_ext_context_optimization": "enhanced_agent_bus._ext_context_optimization",
    "_ext_decision_store": "enhanced_agent_bus._ext_decision_store",
    "_ext_explanation_service": "enhanced_agent_bus._ext_explanation_service",
    "_ext_langgraph": "enhanced_agent_bus._ext_langgraph",
    "_ext_mcp": "enhanced_agent_bus._ext_mcp",
    "_ext_performance": "enhanced_agent_bus._ext_performance",
    "_ext_persistence": "enhanced_agent_bus._ext_persistence",
    "_ext_pqc": "enhanced_agent_bus._ext_pqc",
    "_ext_response_quality": "enhanced_agent_bus._ext_response_quality",
    "_ext_spacetimedb": "enhanced_agent_bus._ext_spacetimedb",
}

EXT_MODULES: list[str] = [k for k in PLUGINS if k.startswith("_ext_")]

EXTRAS: dict[str, str] = {
    "mlflow": "mlflow",
    "numpy": "numpy",
    "pandas": "pandas",
    "sklearn": "scikit-learn",
    "z3": "z3-solver",
}


def available(name: str) -> bool:
    """Return True when the configured module spec can be resolved."""

    module_path = PLUGINS[name]
    try:
        return find_spec(module_path) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def require(name: str) -> str:
    """Return the module path when available, otherwise raise PluginNotAvailable."""

    module_path = PLUGINS[name]
    if not available(name):
        raise PluginNotAvailable(name, module_path, EXTRAS.get(name))
    return module_path


def load_status() -> dict[str, bool]:
    """Return availability status for every registered extension module."""

    return {name: available(name) for name in EXT_MODULES}


__all__ = [
    "EXTRAS",
    "EXT_MODULES",
    "PLUGINS",
    "PluginNotAvailable",
    "available",
    "load_status",
    "require",
]
