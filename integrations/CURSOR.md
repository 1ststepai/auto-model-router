# Cursor integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

## Honest architecture

AMR in Cursor is a **skill / agent behavior policy**. It is not a hook into Cursor billing, quota meters, or the native Auto picker.

| AMR can | AMR cannot |
| --- | --- |
| Classify a task into `fast` / `standard` / `reasoning` / `max` | Replace or reconfigure Cursor's native Auto picker |
| Suggest that tier **and** a concrete picker/effort action from the **local** map | Silently change the model the user has selected |
| Ask the user to switch when the current pick is heavier or lighter than needed | Read Cursor usage, quota, or billing APIs |
| Append a local `.auto-model-router/usage.jsonl` line after an authorized run | Scrape the Cursor usage dashboard or guarantee savings |

Usage estimates come only from that local log plus the optional savings dashboard. They are illustrative relative units, not live Cursor meters.

Cursor's native Auto picker remains a separate feature and may still choose silently.

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

## Local tier → picker mapping

Keep the mapping **out of the portable skill**. Copy [`cursor-tier-map.example.json`](cursor-tier-map.example.json) and fill in the labels that actually appear in this project's Cursor model picker (and effort control, if the build exposes one):

```bash
mkdir -p .auto-model-router
cp integrations/cursor-tier-map.example.json .auto-model-router/cursor-tier-map.json
```

Example shape (placeholders only — use your picker labels):

```json
{
  "fast": { "picker": "<your-fast-model>", "effort": "low" },
  "standard": { "picker": "<your-standard-model>", "effort": "medium" },
  "reasoning": { "picker": "<your-reasoning-model>", "effort": "high" },
  "max": { "picker": "<your-max-model>", "effort": "max" }
}
```

Lookup order for the agent: project `.auto-model-router/cursor-tier-map.json`, then `~/.auto-model-router/cursor-tier-map.json`. If neither exists, name the tier and say `your mapped <tier> model/effort` — do not invent a vendor model name.

Model names in Cursor change. Recalibrate the local file when the picker labels change.

## Wire suggest → gate → concrete picker action

1. Before a model-dependent task, assess context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Decide the confirm gate (`auto_continue`, `confirm`, or `hard_gate`) using the skill policy.
3. Resolve the **local** mapped picker label and effort for that tier.
4. Compare to the current Cursor picker/effort if it is visible. If the current pick is **heavier** than needed, ask the user to switch down. If it is **lighter** than needed for the complexity, ask them to switch up. If you cannot see the current pick, still name the mapped action and ask them to switch if they are not already there.
5. Show a one-line suggestion that includes the **tier and the concrete picker action**, for example:

   ```text
   Auto continues on fast — clear bounded rename. Switch Cursor picker to <your-fast-model> / low effort if the current model is heavier than needed.
   ```

   ```text
   Auto suggests reasoning — security-sensitive review. Switch Cursor picker to <your-reasoning-model> / high effort (current pick is lighter than needed). Confirm the switch, or override: fast, standard, reasoning, or max.
   ```

6. Auto-continue only when the gate allows it **and** the user does not need to switch (already on the mapped pick, or they confirm staying). A required switch is an explicit ask — do not silently take over the picker.
7. After they switch or confirm, run. If a light attempt is clearly too weak, stop for confirm, explain the escalation once, and ask them to switch to the mapped stronger option.

The offline helper can preview the same picker sentence from a map file:

```bash
python3 demo/classify.py --suggest --map integrations/cursor-tier-map.example.json \
  --current-tier max "Rename the variable foo to bar in utils.py"
```

## Verify

Start a new Agent chat (or restart Cursor after a user-wide install).

- A clear rename should print `Auto continues on fast — ...` **and** name the mapped fast picker/effort. If the current pick is heavier, the agent should ask you to switch down.
- A security-sensitive or mixed-boundary task should wait, name the mapped stronger picker/effort, and ask you to switch up if the current pick is lighter than needed.
- Reply `confirm` / switch / override. Cursor's native Auto picker is separate and may still choose silently.

AMR will not show a live Cursor usage remaining figure. After authorized runs you may log locally; the dashboard estimates that log only.
