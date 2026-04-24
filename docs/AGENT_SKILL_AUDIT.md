# Agent Skill and Guidance Audit

Date: 2026-04-24

Scope: `packages/enhanced_agent_bus` instruction files, package-local Claude
Code automation, and local agent configuration.

## Summary

The package now has a smaller active agent surface:

- `AGENTS.md` is the canonical package guide.
- `CLAUDE.md` is a short compatibility pointer for tools that load it directly.
- Two package-local skills remain active.
- One package-local reviewer agent remains active.
- One overlapping agent prompt was removed.
- Long OpenEvolve background guidance was replaced with a concise local contract.

No global/user skill directories were modified.

## Files Audited

| Surface | Decision | Reason |
| --- | --- | --- |
| `AGENTS.md` | Keep, trimmed | Canonical package guidance; now concise, repo-specific, and command-focused. |
| `CLAUDE.md` | Keep as pointer | Avoids duplicating structure and contracts already in `AGENTS.md`. |
| `.claude/settings.json` | Keep, minimal | Provides local guard and verification hooks without forcing plugin state. |
| `.claude/hooks/eab-guard-preuse.sh` | Keep | Blocks recurring high-risk edit patterns before they enter the tree. |
| `.claude/hooks/eab-python-postuse.sh` | Keep | Fast, focused feedback for Python edits. |
| `.claude/skills/eab-focused-verify/SKILL.md` | Keep | Clear trigger and measurable output for focused package verification. |
| `.claude/skills/eab-stop-gate-review/SKILL.md` | Keep | Distinct review workflow for the immediately previous code-changing turn. |
| `.claude/agents/eab-security-governance-reviewer.md` | Keep | Distinct security/governance review role. |
| `.claude/agents/eab-verification-mapper.md` | Removed | Overlapped with `eab-focused-verify`; maintaining both created duplicate routing. |
| `openevolve_adapter/AGENTS.md` | Keep, trimmed | Subdirectory behavior differs, but the old file loaded too much background by default. |
| Other subdirectory `AGENTS.md` files | Keep | Short local deltas, typically 27-57 lines; no obvious duplicate skill behavior. |

## Skills Kept

### `eab-focused-verify`

Trigger: Use after package-local Python, config, or agent automation edits when
the task needs a focused verification gate rather than a full package regression.

Inputs:

- Changed file list, or enough task context to derive one from `git diff --name-only`.
- Optional module/test targets when the impacted package area is already known.

Outputs:

- Exact verification commands run.
- Pass/fail result for each command.
- Remaining risks, including skipped full-suite gates.

Reason kept: It encodes the package's recurring verification shape: `ruff`,
`py_compile`, targeted pytest with `--import-mode=importlib`, optional module-mode
mypy with `/tmp` cache, and `git diff --check`.

### `eab-stop-gate-review`

Trigger: Use only when reviewing the immediately previous code-changing turn in
this package.

Inputs:

- The immediately previous assistant/agent turn.
- Exact changed files from that turn.
- Same-turn verification output, when present.

Outputs:

- `ALLOW:` or `BLOCK:` first.
- Findings with file and line references when blocking.
- Verification gaps only when they affect ship confidence.

Reason kept: Stop-gate reviews are frequent in this repo and have strict scope
rules. Keeping this as a narrow user-invoked skill prevents generic review drift.

## Skills Merged

None. There were only two package-local skills and they serve distinct jobs.

## Skills Removed or Quarantined

No package-local skills were removed.

The overlapping prompt `.claude/agents/eab-verification-mapper.md` was removed,
not quarantined, because it duplicated the command-planning portion of
`eab-focused-verify` and had no distinct trigger.

## Remaining Agent Prompt

### `eab-security-governance-reviewer`

Trigger: Use when reviewing diffs that touch auth, MACI, OPA, policy, JWT,
tenant isolation, capability passports, middleware, or governance behavior.

Inputs:

- Assigned files or a concrete diff.

Outputs:

- Findings first, ordered by severity.
- File and line references.
- Residual verification risk when no findings are present.

Reason kept: This is materially different from generic review because this
package's highest-risk failures are fail-open governance and tenant-boundary bugs.

## Hook Decisions

| Hook | Decision | Input | Output |
| --- | --- | --- | --- |
| `eab-guard-preuse.sh` | Keep | Claude Code `PreToolUse` JSON for write/edit tools | Exit `0` allow, exit `2` block with guardrail message |
| `eab-python-postuse.sh` | Keep | Claude Code `PostToolUse` JSON for write/edit tools | Runs `ruff check` and `py_compile` for touched Python files |

The hooks intentionally avoid `jq` and new dependencies. They use Python from
the existing runtime and shell only.

## Configuration Decisions

- Package-local plugin enabling was not kept in `.claude/settings.json`; plugin
  installation and enabling should remain user/global state.
- Permissions remain limited to local verification, git inspection, and the two
  local hook scripts.
- Destructive git and broad removal commands stay denied.

## Remaining Risks

- The repository still has many user/global installed skills outside this package;
  they were out of write scope for this package cleanup.
- Subdirectory `AGENTS.md` files were audited by size and purpose, not rewritten
  wholesale. Revisit only when editing those subtrees.
- The package-level top import still has a large context/runtime footprint because
  `__init__.py` eagerly re-exports many runtime and extension surfaces.
