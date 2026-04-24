#!/usr/bin/env bash
# Claude Code PreToolUse guard for enhanced_agent_bus package edits.
# Exit 0 allows the tool call. Exit 2 blocks it.

set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "[eab-guard] python3 not found — blocking as fail-closed" >&2; exit 2; }

HOOK_INPUT=$(cat)

python3 - "$HOOK_INPUT" <<'PY'
import json
import re
import sys
from pathlib import Path

try:
    payload = json.loads(sys.argv[1])
except (json.JSONDecodeError, IndexError):
    print("[eab-guard] malformed or missing payload — blocking as fail-closed", file=sys.stderr)
    sys.exit(2)

tool_input = payload.get("tool_input") or {}
records: list[tuple[str, str]] = []

file_path = tool_input.get("file_path")
if isinstance(file_path, str):
    text = "\n".join(
        str(tool_input.get(key) or "")
        for key in ("content", "new_string")
    )
    records.append((file_path, text))

for edit in tool_input.get("edits") or []:
    if not isinstance(edit, dict):
        continue
    edit_path = edit.get("file_path") or file_path
    if isinstance(edit_path, str):
        records.append((edit_path, str(edit.get("new_string") or "")))

blocked_patterns = (
    "__pycache__/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    "htmlcov/",
    "build/",
    "dist/",
    ".egg-info/",
    "coverage.xml",
)

violations: list[str] = []

for raw_path, new_text in records:
    normalized = raw_path.replace("\\", "/")
    basename = Path(normalized).name

    if basename == ".env" or basename.startswith(".env."):
        violations.append(f"{raw_path}: do not edit environment secret files; update examples/docs instead")

    if any(pattern in normalized for pattern in blocked_patterns):
        violations.append(f"{raw_path}: generated, cache, coverage, or build artifact path is protected")

    if re.search(r"enhanced_agent_bus\.middleware(\b|\.)", new_text):
        violations.append(
            f"{raw_path}: import from enhanced_agent_bus.middlewares instead; enhanced_agent_bus.middleware is deleted"
        )

    if "JWT_ALGORITHM" in new_text and "resolve_jwt_algorithm" not in new_text:
        violations.append(
            f"{raw_path}: JWT algorithm parsing must use _compat.security.jwt_algorithms.resolve_jwt_algorithm"
        )

if violations:
    print("[eab-guard] BLOCKED:", file=sys.stderr)
    for violation in violations:
        print(f"- {violation}", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
PY
