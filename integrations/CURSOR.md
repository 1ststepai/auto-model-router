# Cursor integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

## Install

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

## Wire suggest → confirm

1. Before a model-dependent task, assess context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Show `Auto suggests <tier> — <reason>. Confirm to run, or override...` in chat.
3. Wait for the user's confirmation or model/tier override.
4. Use Cursor's model picker and available effort controls to map the confirmed tier, then run.
5. If the attempt is clearly too light, explain the escalation once and select a stronger configured option.

Cursor's model names change over time, so keep the mapping local to the project's available picker rather than hard-coding vendor names in the skill.

## Verify

Start a new Agent chat (or restart Cursor after a user-wide install), ask for a moderate task without naming a model, and confirm that the `Auto suggests <tier> — <reason>...` line appears before edits. Reply `confirm` or override the tier. Cursor's native Auto picker is separate and may still choose silently.
