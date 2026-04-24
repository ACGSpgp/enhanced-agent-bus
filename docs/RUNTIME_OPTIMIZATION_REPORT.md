# Runtime Optimization Report

Date: 2026-04-24

Scope: targeted startup/import checks and safe runtime compatibility fixes for
`packages/enhanced_agent_bus`.

## Baseline Observations

Baseline import checks were run from `/home/martin/Downloads/ACGS/packages` with:

```bash
PYTHONPATH=/home/martin/Downloads/ACGS/packages python -X importtime -c 'import enhanced_agent_bus'
PYTHONPATH=/home/martin/Downloads/ACGS/packages python -X importtime -c 'import enhanced_agent_bus.api.app'
```

Initial results:

- `import enhanced_agent_bus` failed before timing completed.
- Failure: `AttributeError: module 'enhanced_agent_bus._compat.metrics' has no attribute 'set_service_info'`.
- `import enhanced_agent_bus.api.app` also failed after that was fixed.
- Failure: `TypeError: NoneType takes no arguments` while defining SQLAlchemy ORM classes through the standalone DB session shim.

These were startup blockers, not micro-optimizations.

## Files Inspected

- `enhanced_agent_bus/__init__.py`
- `api/app.py`
- `bus/core.py`
- `_compat/metrics/__init__.py`
- `_compat/metrics/_registry.py`
- `_compat/metrics/noop.py`
- `_compat/database/session.py`
- `multi_tenancy/orm_models.py`
- `multi_tenancy/db_repository.py`
- `routes/sessions/*`
- `api/tests/test_app_coverage.py`
- `tests/test_ext_shim_fallbacks.py`

## Bottlenecks Found

### Startup blocker: metrics compat export

`bus/core.py` imports `enhanced_agent_bus._compat.metrics` and, when the module
exists, expects `set_service_info`. The standalone fallback exported metric
factories but not `set_service_info`, so top-level package import failed.

### Startup blocker: database session fallback

`_compat.database.session` set `Base = None` when the monorepo shared database
session module was unavailable. In standalone mode with SQLAlchemy installed,
`multi_tenancy.orm_models` then failed at class definition time.

### Remaining cold-start cost

After startup blockers were fixed, import-time output showed the top-level package
still eagerly imports a broad runtime surface. Notable cumulative costs in this
sandbox included:

- `enhanced_agent_bus` top-level import: about 2.85 seconds average.
- `enhanced_agent_bus.api.app` import: about 3.24 seconds average.
- `_ext_context_memory`: about 13.8 ms cumulative.
- `_ext_mcp`: about 10.9 ms cumulative.
- `routes.tenants`: about 66 ms cumulative during API app import.
- `multi_tenancy.orm_models`: about 29.5 ms cumulative during API app import.

The dominant cost remains eager top-level imports from `__init__.py`, not a
single common request-path function.

## Changes Made

### `_compat/metrics/__init__.py`

Added a no-op standalone `set_service_info(...)` fallback and exported it through
`__all__`.

Behavior impact: preserves current metrics API shape when shared metrics are
unavailable; no metrics are emitted in fallback mode.

### `_compat/database/session.py`

Changed standalone fallback behavior to create a SQLAlchemy declarative base when
SQLAlchemy is installed. It still falls back to `Base = None` only when SQLAlchemy
itself is unavailable.

Behavior impact: standalone ORM model imports now work when the package's
SQLAlchemy-backed surfaces are importable.

### `tests/test_ext_shim_fallbacks.py`

Added regression coverage for:

- Top-level package import under compat fallbacks.
- Standalone database session fallback providing an ORM base.

## Measurements

After fixes, the import checks completed.

Three-process timing sample:

```text
enhanced_agent_bus: mean=2853.99 ms min=2809.79 max=2937.69
enhanced_agent_bus.api.app: mean=3240.98 ms min=3079.48 max=3523.24
```

Single-process sanity check:

```text
enhanced_agent_bus: 3004.73 ms
enhanced_agent_bus.api.app: 277.80 ms
```

The second number in the single-process sanity check is incremental after
`enhanced_agent_bus` had already been imported.

## Tests and Checks Run

```bash
python -m pytest tests/test_ext_shim_fallbacks.py -q --import-mode=importlib
python -m pytest tests/test_ext_shim_fallbacks.py api/tests/test_app_coverage.py::TestCreateApp::test_create_app_returns_fastapi_instance -q --import-mode=importlib
python -m ruff check _compat/metrics/__init__.py _compat/database/session.py tests/test_ext_shim_fallbacks.py api/app.py
```

Results:

- `tests/test_ext_shim_fallbacks.py`: 4 passed before DB fallback test, then 5 passed after adding it.
- Combined targeted app/import check: 6 passed.
- Ruff: passed.

## Remaining Performance Risks

- `enhanced_agent_bus/__init__.py` eagerly imports broad runtime modules and
  extension surfaces. This is the largest remaining cold-start cost.
- `api/app.py` creates the default app at import time and registers optional
  routers immediately. This is public behavior today, so it was not changed.
- Optional routers such as Visual Studio, Policy Copilot, session governance, and
  tenant routes add startup work even when a deployment may not use them.
- App import logs warnings/info during import, which adds noise and small overhead.
- Broad LangGraph tests previously showed teardown hangs; this report did not
  change that area.

## Next Recommended Optimizations

1. Introduce a measured lazy-export strategy for `enhanced_agent_bus.__init__`
   using `__getattr__` for rarely used extension surfaces, while preserving
   existing `from enhanced_agent_bus import X` behavior.
2. Add an environment/config switch to disable optional API routers at app
   creation time for lean deployments.
3. Move noisy import-time optional router logging behind startup diagnostics or
   debug-level logging.
4. Add an import-budget test for `enhanced_agent_bus` and `enhanced_agent_bus.api.app`
   so future broad re-export additions are visible.
5. Profile actual request handlers separately from cold start before changing
   common-path code.
