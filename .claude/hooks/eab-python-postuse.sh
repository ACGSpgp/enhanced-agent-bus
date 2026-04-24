#!/usr/bin/env bash
# Claude Code PostToolUse verifier for focused Python edits.
# This is intentionally best-effort: it reports failures without blocking the edit loop.

set -uo pipefail

HOOK_INPUT=$(cat)
mapfile -t PY_FILES < <(
  python3 -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    raise SystemExit(0)

tool_input = payload.get("tool_input") or {}
paths = []
file_path = tool_input.get("file_path")
if isinstance(file_path, str):
    paths.append(file_path)
for edit in tool_input.get("edits") or []:
    if isinstance(edit, dict):
        edit_path = edit.get("file_path") or file_path
        if isinstance(edit_path, str):
            paths.append(edit_path)

for path in sorted({path for path in paths if path.endswith(".py")}):
    print(path)
' <<<"$HOOK_INPUT"
)

if [ "${#PY_FILES[@]}" -eq 0 ]; then
  exit 0
fi

EXISTING=()
for file in "${PY_FILES[@]}"; do
  if [ -f "$file" ]; then
    EXISTING+=("$file")
  fi
done

if [ "${#EXISTING[@]}" -eq 0 ]; then
  exit 0
fi

echo "[eab-python-postuse] ruff check ${EXISTING[*]}" >&2
python -m ruff check "${EXISTING[@]}" >&2 || STATUS=$?

echo "[eab-python-postuse] py_compile ${EXISTING[*]}" >&2
python -m py_compile "${EXISTING[@]}" >&2 || STATUS=$?

exit "${STATUS:-0}"
