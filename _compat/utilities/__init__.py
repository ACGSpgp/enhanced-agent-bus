"""Shim package for src.core.shared.utilities."""

from __future__ import annotations

from .dependency_registry import (  # noqa: F401
    DependencyRegistry,
    FeatureFlag,
    get_dependency_registry,
)

__all__ = ["DependencyRegistry", "FeatureFlag", "get_dependency_registry"]
