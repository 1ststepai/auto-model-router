# Roll out Auto Model Router across 1stStep builds

Canonical policy lives in this repo:
[`skills/auto-model-router/SKILL.md`](../skills/auto-model-router/SKILL.md)

As of the local/cloud merge on `main`, every classify result also has `mode` (`local` | `cloud`). Mode is advisory. It does not launch Cursor Cloud Agents.

## User-wide (all local sessions)

From a clone of this repo:

```bash
./scripts/apply.sh --no-open
```

That copies the skill into Cursor / Claude / Codex / Gemini user skill dirs.

## Per-repo (cloud agents and teammates)

Commit a pointer skill so background agents load the same policy:

```text
.cursor/skills/auto-model-router/SKILL.md
.agents/skills/auto-model-router/SKILL.md   # Codex
.claude/skills/auto-model-router/SKILL.md
```

Keep the pointer short. Do not fork the rubric in each product repo.

## Active 1stStep targets

Priority agent-tooling repos: `1ststep-os`, `codefriends`, `agent-memory`, `main-website`.
Product apps can take the same pointer when an agent works in them.
