# Cursor integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

## Install

**Plugin (Teams / Enterprise):** Dashboard → Plugins & MCPs → Import from Repo → `https://github.com/1ststepai/auto-model-router`, then Customize → Plugins → install Auto Model Router. Local fallback: copy this clone into `~/.cursor/plugins/local/auto-model-router`, or run `./scripts/apply.sh`. See [`../INSTALL.md`](../INSTALL.md).

From a project containing this repository:

```bash
mkdir -p .cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force .cursor\skills\auto-model-router | Out-Null
Copy-Item skills\auto-model-router\SKILL.md .cursor\skills\auto-model-router\SKILL.md
```

For a user-wide setup, use `~/.cursor/skills/auto-model-router/SKILL.md` on macOS/Linux or `%USERPROFILE%\.cursor\skills\auto-model-router\SKILL.md` on Windows. The PowerShell equivalent is:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.cursor\skills\auto-model-router" | Out-Null
Copy-Item skills\auto-model-router\SKILL.md "$env:USERPROFILE\.cursor\skills\auto-model-router\SKILL.md"
```

An optional always-apply `.cursor/rules/auto-model-router.mdc` can point at the project skill. Keep the rule short; the full example is in [`../INSTALL.md`](../INSTALL.md).

## Wire suggest → gate → run

1. Before a model-dependent task, assess context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Decide the confirm gate (`auto_continue`, `confirm`, or `hard_gate`) using the skill policy.
3. Show `Auto continues on <tier> — <reason>.` or `Auto suggests <tier> — <reason>. Confirm...` in chat.
4. Auto-continue only when the gate allows it; otherwise wait for confirmation or a model/tier override.
5. Use Cursor's model picker and available effort controls to map the gated tier, then run.
6. If the attempt is clearly too light, stop for confirm, explain the escalation once, and select a stronger configured option.

Cursor's model names change over time, so keep the mapping local to the project's available picker rather than hard-coding vendor names in the skill.

## Verify

Start a new Agent chat (or restart Cursor after a user-wide install). A clear rename should print `Auto continues on fast — ...` and start. A security-sensitive or mixed-boundary task should wait. Reply `confirm` or override the tier when asked. Cursor's native Auto picker is separate and may still choose silently.
