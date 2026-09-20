# Savings Desk

**Product win:** the user **opts in** to a usage audit, then receives **automation** that acts on it. Cross-host: Cursor, Claude Code, Codex/OpenAI, Gemini-style agents.

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
  "boundaryGatedConfirms": false
}
```

- `hosts[]` — which adapters you care about (audit still reads whatever `host` is on each log line).
- `usageLogPath` — empty means `~/.auto-model-router/logs/usage.jsonl`. Project copies may also live at `.auto-model-router/usage.jsonl`.

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

The dashboard “Savings Desk Pro” panel is labeled as a stub. There is no payment form.

## How to try

```bash
# 1. Opt in (writes ~/.auto-model-router/config.json)
./scripts/apply.sh --enable-audit --no-open

# 2. Audit local logs (sample is used if your jsonl is empty; it is labeled)
python3 scripts/audit_usage.py --force

# 3. Apply automation: local maps + boundaryGatedConfirms + optional weekly digest
python3 scripts/apply_recommendations.py --enable-weekly-review
# or: ./scripts/apply.sh --enable-audit --apply-recommendations --no-open

# 4. Open the dashboard
#    ~/.auto-model-router/demo/dashboard.html  or  demo/dashboard.html
```

Fill `<your-fast-model>` placeholders in `~/.auto-model-router/cursor-tier-map.json` (and the Claude/Codex stubs) with labels from **your** picker. AMR will not flip the host control for you.

## Honesty

- Relative units: `fast=1x`, `standard=3x`, `reasoning=8x`, `max=20x`. Estimates vs always-max / always-reasoning, not measured vendor dollars.
- Boundary-gated confirms reduce confirm-fatigue; they are documented in [`docs/boundary-gated-confirms.md`](boundary-gated-confirms.md).
- Complementary context tools are peers — see [`docs/STACK.md`](STACK.md).
