---
name: eab-focused-verify
description: Run the focused enhanced-agent-bus verification gate for touched Python files and package cohorts.
disable-model-invocation: true
---

# EAB Focused Verify

Use this when a change touched `packages/enhanced_agent_bus` and the goal is to prove the narrow claim without running the full package regression.

## Workflow

1. Establish scope:

```bash
git status --short --untracked-files=normal
git diff --name-only --diff-filter=ACMRT
```

2. For touched Python files that still exist, run:

```bash
python -m ruff check <files>
python -m py_compile <files>
```

3. If the change is type-related or in a typed cohort, run mypy with an external cache:

```bash
MYPY_CACHE_DIR=/tmp/eab_mypy_cache python -m mypy <modules-or-files> --config-file enhanced_agent_bus/mypy.ini
```

When running from the package directory, use the package-local config path:

```bash
MYPY_CACHE_DIR=/tmp/eab_mypy_cache python -m mypy <modules-or-files> --config-file mypy.ini
```

4. Run the narrowest relevant pytest command. Prefer package-local tests first:

```bash
python -m pytest <tests-or-package-tests> -q --import-mode=importlib
```

5. Always finish with:

```bash
git diff --check
```

## Reporting

Report:

- Changed files under verification.
- Exact commands that passed.
- Exact failures or skipped gates.
- Known residual risk, especially hangs, missing optional dependencies, or unrelated dirty worktree entries.
