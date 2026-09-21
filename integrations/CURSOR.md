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

## Wire suggest → gate

1. Before a model-dependent task, assess context and classify it as `fast`, `standard`, `reasoning`, or `max`. Decide the gate (`auto_continue`, `confirm`, `hard_gate`).
2. Show `Auto continues on fast — …` or `Auto suggests <tier> — <reason>. Confirm to run, or override...` in chat. If `.auto-model-router/cursor-tier-map.json` exists, name the mapped picker/effort (placeholders only — never invent a vendor name).
3. Auto-continue only clear reversible `fast`. Wait for confirmation on spendy / high-risk work. Optional: copy [`../hooks/cursor.hooks.json`](../hooks/cursor.hooks.json) to `.cursor/hooks.json` so PreToolUse is denied until confirm.
4. Use Cursor's model picker and available effort controls to map the gated tier, then run.
5. If the attempt is clearly too light, stop for confirm, explain the escalation once, and select a stronger configured option.

Cursor's model names change over time, so keep the mapping local to the project's available picker rather than hard-coding vendor names in the skill. Copy [`cursor-tier-map.example.json`](cursor-tier-map.example.json) and fill in your labels. `python3 scripts/detect_active.py` only reads local env/config/log.

## Verify

Start a new Agent chat (or restart Cursor after a user-wide install). A clear rename should print `Auto continues on fast`. A moderate or security task should wait. Reply `confirm` or override the tier. Cursor's native Auto picker is separate and may still choose silently.
