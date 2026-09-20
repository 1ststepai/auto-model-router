# Savings Desk

**Product win:** the user **opts in** to a usage audit of the model they are **actually using**, then is asked whether to **optimize**. Automation runs only after yes. Cross-host: Cursor, Claude Code, Codex/OpenAI, Gemini-style agents.

Flow: **detect active model → audit that usage → ask “optimize?” → if yes, automate.**

This is the MIT open-core desk. It reads **local** `usage.jsonl` only. It does not scrape Cursor/Claude/OpenAI/Gemini billing UIs, does not claim a live quota API, and does not run a production routing proxy.

## Consent

Nothing is appended to the usage log until `auditOptIn` is `true` in `~/.auto-model-router/config.json` (Windows: `%USERPROFILE%\.auto-model-router\config.json`).

```json
{
  "openDashboardOnApply": true,
  "weeklyReview": false,
  "auditOptIn": false,
  "hosts": ["cursor", "claude-code", "codex"],
  "usageLogPath": "",
  "boundaryGatedConfirms": false,
  "codefriendsUrl": ""
}
```

- `hosts[]` — which adapters you care about (audit still reads whatever `host` is on each log line).
- `usageLogPath` — empty means `~/.auto-model-router/logs/usage.jsonl`. Project copies may also live at `.auto-model-router/usage.jsonl`.
- `currentHost` / `currentTier` / `currentModel` — optional **declared** picker context. Live Cursor/Claude/OpenAI pickers and meters cannot be read. You can also pass `--host`, `--current-tier`, `--current-model`, or `AMR_HOST` / `AMR_CURRENT_TIER` / `AMR_CURRENT_MODEL`. If none of those are set, the latest `usage.jsonl` row is used.
- `codefriendsUrl` — optional invite link (http/https). After a successful audit, and again after you say yes to optimize, the CLI/dashboard may ask if you want to join **CodeFriends**. Never required. If this is empty, the ask says to set `codefriendsUrl` rather than inventing a domain.

### Collected (when opted in)

`timestamp`, `tier`, `suggested_tier`, `confirmed`, `overridden`, `host`, `task_kind`, `gate`

### Never collected

Prompts, task text, code, secrets, customer data, vendor credentials, billing/quota API payloads.

See the skill schema in [`SKILL.md`](../SKILL.md).

## Free skill vs Paid Desk

| | Free (this repo / skill) | Savings Desk Pro (placeholder) |
| --- | --- | --- |
| Suggest → confirm routing skill | Yes | Yes |
| Local `usage.jsonl` + opt-in flag | Yes | Yes |
| CLI audit + weekly digest | Yes | Yes |
| Apply local tier maps + boundary-gate flag | Yes | Yes |
| HTML dashboard (hosts filter, relative savings) | Yes | Yes |
| Export / shareable report | Stub only | Planned |
| Team rollup across machines | Stub only | Planned (solo vs team SKU) |
| Invoice / CSV reconcile | Not in MVP | Optional later — you upload the file |
| Live vendor meter scrape | Never | Never |

Pricing placeholders (not a checkout, not a quote):

- **Solo** — local desk + export. Price TBD.
- **Team** — rollup + shared policy maps. Price TBD.

The dashboard does **not** lead with a paid upsell. A collapsed “later: team export” note sits at the bottom. There is no payment form.

## How to try

```bash
# 1. Opt in
./scripts/apply.sh --enable-audit --no-open

# 2. Detect the active pick (declared flags/config, else latest local log row)
python3 scripts/detect_active.py
#    or: python3 scripts/detect_active.py --current-tier max --host cursor

# 3. Audit that pick first (sample is labeled if your jsonl is empty)
python3 scripts/audit_usage.py --force

# 4. Only if you want to optimize:
python3 scripts/apply_recommendations.py --yes --enable-weekly-review

# 5. Dashboard: demo/dashboard.html — declare host/tier, read the active burn, then Yes on optimize
```

Fill `<your-fast-model>` placeholders in `~/.auto-model-router/cursor-tier-map.json` (and the Claude/Codex stubs) with labels from **your** picker. AMR will not flip the host control for you.

## Honesty

- Relative units: `fast=1x`, `standard=3x`, `reasoning=8x`, `max=20x`. Estimates vs always-max / always-reasoning, not measured vendor dollars.
- Boundary-gated confirms reduce confirm-fatigue; they are documented in [`docs/boundary-gated-confirms.md`](boundary-gated-confirms.md).
- Complementary context tools are peers — see [`docs/STACK.md`](STACK.md).
