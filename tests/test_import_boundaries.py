"""Import-boundary checks for enhanced_agent_bus.

enhanced_agent_bus is a service-package. It may import from acgs_lite,
src.core.shared, and acgs_deliberation. It must not import from:
  - constitutional_swarm (wrong direction — swarm uses EAB, not vice versa)
  - mhc (lateral/higher-level)

The _compat/ subpackage intentionally re-exports src.core.shared.* during the
migration away from the monolith namespace — those imports are excluded from
this check.

KNOWN_VIOLATIONS tracks existing debt. The test fails when:
  - a NEW violation appears (add to KNOWN_VIOLATIONS after review), or
  - a KNOWN violation disappears (remove from the set — debt paid off).
"""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PREFIXES = (
    "constitutional_swarm",
    "mhc",
)

# Pre-existing violations being tracked.
KNOWN_VIOLATIONS: set[str] = set()  # Empty — governance_core.py no longer imports constitutional_swarm.


def _iter_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None:
                imports.append(node.module)
    return imports


def _is_excluded(path: Path) -> bool:
    """Skip test files and the _compat shim (intentional re-export layer)."""
    parts = path.parts
    return (
        "test" in path.name
        or path.name.startswith("_test")
        or "tests" in parts
        or "_compat" in parts
    )


def test_runtime_source_import_boundaries() -> None:
    found: set[str] = set()

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if _is_excluded(path):
            continue
        rel = path.relative_to(SOURCE_ROOT)
        key_prefix = str(rel)

        for module in _iter_imports(path):
            for prefix in FORBIDDEN_PREFIXES:
                if module == prefix or module.startswith(prefix + "."):
                    found.add(f"{key_prefix}: {module}")
                    break

    new_violations = found - KNOWN_VIOLATIONS
    cleared_violations = KNOWN_VIOLATIONS - found

    messages: list[str] = []
    if new_violations:
        messages.append(
            "NEW boundary violations (fix or add to KNOWN_VIOLATIONS with review comment):\n"
            + "\n".join(f"  {v}" for v in sorted(new_violations))
        )
    if cleared_violations:
        messages.append(
            "Violations no longer present — remove from KNOWN_VIOLATIONS:\n"
            + "\n".join(f"  {v}" for v in sorted(cleared_violations))
        )

    assert not messages, "\n\n".join(messages)
