# Claude integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

## Install

**Plugin:** `/plugin marketplace add 1ststepai/auto-model-router` then `/plugin install auto-model-router@auto-model-router` and `/reload-plugins`. See [`../INSTALL.md`](../INSTALL.md).

For a project-local Claude Code setup:

```bash
mkdir -p .claude/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force .claude\skills\auto-model-router | Out-Null
Copy-Item skills\auto-model-router\SKILL.md .claude\skills\auto-model-router\SKILL.md
```

For a user-wide copy, use `~/.claude/skills/auto-model-router/SKILL.md` on macOS/Linux/WSL or `%USERPROFILE%\.claude\skills\auto-model-router\SKILL.md` on native Windows. You can also include `@.claude/skills/auto-model-router/SKILL.md` from a project `CLAUDE.md`.

## Wire suggest → confirm

1. Classify the request using the neutral four-tier rubric.
2. Tell the user the suggested tier and short reason before starting model work.
3. Wait for `confirm` or an explicit tier/model override.
4. Select the configured Claude model or effort setting for that tier, then run.
5. After a failed light attempt, state that you are escalating and continue with a stronger configured model/effort.

Do not bake specific Claude model names into the portable skill; map the tiers to the models enabled for the project. Savings Desk can write a local stub at `~/.auto-model-router/claude-tier-map.json` from [`claude-tier-map.example.json`](claude-tier-map.example.json) after you opt in to the audit. Fill the placeholders; AMR does not call Anthropic billing APIs.

## Verify

Start a new Claude Code session after installing. Ask for a moderate task without choosing a model or effort, and check for the `Auto suggests <tier> — <reason>...` line before file changes. Reply `confirm` or override explicitly. Project files are the dependable choice for cloud sessions; a local `~/.claude` copy does not automatically follow a remote checkout.
