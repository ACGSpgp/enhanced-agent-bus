# Enhanced Agent Bus

Use [AGENTS.md](AGENTS.md) as the canonical package guide. This file exists for
tools that load `CLAUDE.md` directly.

Key reminders:

- Import from `enhanced_agent_bus.*`.
- New middleware goes under `middlewares/`; never import `enhanced_agent_bus.middleware`.
- Prefer `context_memory/` for new context or memory work.
- Fail closed on auth, policy, MACI, OPA, tenant, and governance paths.
- Use focused verification before full-package tests.

Common package-local checks:

```bash
python -m ruff check <changed-python-files>
python -m py_compile <changed-python-files>
python -m pytest <targeted-tests> -q --import-mode=importlib
git diff --check
```

For mypy, run from `/home/martin/Downloads/ACGS/packages` with `/tmp` cache as
shown in [AGENTS.md](AGENTS.md).
