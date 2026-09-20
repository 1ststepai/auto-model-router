# Codex integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

## Install

**Plugin:** `codex plugin marketplace add 1ststepai/auto-model-router` then `codex plugin add auto-model-router@auto-model-router`. See [`../INSTALL.md`](../INSTALL.md).

Add the skill to project instructions, commonly `AGENTS.md`:

```bash
cat skills/auto-model-router/SKILL.md >> AGENTS.md
```

Prefer a marked section that points to the policy when `AGENTS.md` already contains project rules. If your Codex setup supports Agent Skills, the current project path is `.agents/skills/auto-model-router/SKILL.md`; user-wide paths are `~/.agents/skills/auto-model-router/SKILL.md` on macOS/Linux and `%USERPROFILE%\.agents\skills\auto-model-router\SKILL.md` on Windows. On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force .agents\skills\auto-model-router | Out-Null
Copy-Item skills\auto-model-router\SKILL.md .agents\skills\auto-model-router\SKILL.md
```

Some older/configured installs also support `$CODEX_HOME/skills` (normally `~/.codex/skills` or `%USERPROFILE%\.codex\skills`).

## Wire suggest → gate → run

1. Read task context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Present the suggestion and one-line reason to the user.
3. Auto-continue only when the gate allows it; otherwise wait for confirmation or a tier/model/effort override before dispatch.
4. Map the gated tier to the Codex model and/or reasoning effort configured for the project, then run.
5. After an insufficient light attempt, stop for confirm, escalate toward `reasoning` or `max`, and explain the change once.

Tier labels are deliberately not Codex product names. Keep the mapping in project instructions so it can evolve with the available Codex models.

## Verify

Start a new Codex run/session after changing `AGENTS.md` or adding a skill. A clear rename should auto-continue. A security-sensitive or mixed-boundary task should show the `Auto suggests <tier> — <reason>...` line and wait for `confirm` or an explicit override. Put the files in the repository for cloud/background runs.
