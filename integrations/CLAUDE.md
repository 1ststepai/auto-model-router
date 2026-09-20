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

## Wire suggest → gate → run

1. Classify the request using the neutral four-tier rubric and the confirm-gate policy.
2. Tell the user the suggested tier and short reason before starting model work.
3. Auto-continue only when the gate allows it; otherwise wait for `confirm` or an explicit tier/model override.
4. Select the configured Claude model or effort setting for that tier, then run.
5. After a failed light attempt, stop for confirm, state that you are escalating, and continue with a stronger configured model/effort.

Do not bake specific Claude model names into the portable skill; map the tiers to the models enabled for the project.

## Verify

Start a new Claude Code session after installing. A clear rename should auto-continue with `Auto continues on fast — ...`. A security-sensitive or mixed-boundary task should wait. Reply `confirm` or override explicitly when asked. Project files are the dependable choice for cloud sessions; a local `~/.claude` copy does not automatically follow a remote checkout.
