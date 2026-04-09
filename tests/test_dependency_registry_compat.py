"""Regression tests for enhanced_agent_bus dependency registry compat exports."""

from enhanced_agent_bus._compat.utilities import DependencyRegistry, get_dependency_registry


def test_get_dependency_registry_exported() -> None:
    registry = get_dependency_registry()

    assert isinstance(registry, DependencyRegistry)
    assert get_dependency_registry() is registry
