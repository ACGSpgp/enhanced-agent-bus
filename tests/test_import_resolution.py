from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_workspace_import_resolution_prefers_current_checkout() -> None:
    packages_dir = Path(__file__).resolve().parents[2]
    original_path = list(sys.path)
    # Evict cached enhanced_agent_bus entries so find_spec resolves against
    # sys.path rather than returning the already-loaded module's spec.
    evicted = {k: v for k, v in sys.modules.items() if k == "enhanced_agent_bus" or k.startswith("enhanced_agent_bus.")}
    try:
        for k in evicted:
            del sys.modules[k]
        sys.path[:] = [str(packages_dir), *[p for p in sys.path if p != str(packages_dir)]]
        spec = importlib.util.find_spec("enhanced_agent_bus")
        assert spec is not None
        assert spec.origin is not None
        assert Path(spec.origin).resolve().is_relative_to(packages_dir.resolve())
    finally:
        sys.path[:] = original_path
        sys.modules.update(evicted)


def test_test_harness_blocks_stale_external_checkout_paths() -> None:
    stale_entry = "/home/martin/Documents/acgs-main/packages"
    # intentional: sys.path manipulation is the test subject here, not a bootstrap
    sys.path.insert(0, stale_entry)
    assert stale_entry not in sys.path
