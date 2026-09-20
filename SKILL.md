---
name: auto-model-router
description: "Before choosing a model or effort for substantial work, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), suggest that tier and why, wait for user confirmation or an override, then run it through the host's adapter. Prefer lighter for reversible work, never under-provision security or irreversible actions, and escalate after a failed light attempt."
---

# Auto model router

**name:** auto-model-router  
**description:** Before choosing a model or effort for substantial work, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), suggest that tier and why, wait for user confirmation or an override, then run it through the host's adapter. Prefer lighter for reversible work, never under-provision security or irreversible actions, and escalate after a failed light attempt.

## Purpose

Provide one portable routing policy for Cursor, Claude, Codex, and other multi-model coding agents. The policy reduces manual model picking while keeping the user in control. It is provider-agnostic: the tier is a capability label, not a vendor model name.

## When to use

Use before dispatching substantial coding-agent work or choosing a model/effort when the choice is user-visible. Do not add a routing lecture to an unrelated answer. If the user explicitly names a model or effort, honor it; only classify when the user asks Auto to choose or leaves the choice open.

## Core procedure: context → classify → suggest → confirm → run

1. **Read context.** Assess scope, involved files or systems, ambiguity, required judgment, security or external-action risk, and whether the work is reversible.
2. **Honor an explicit override.** If the user already chose a model, provider, effort, or tier, use that choice and skip an unsolicited suggestion.
3. **Classify** the open choice into the lightest sufficient tier using the rubric below. An optional offline helper is `demo/classify.py` or `demo/classify.py --suggest`; it is only a heuristic second opinion.
4. **Suggest before dispatch.** Give the tier and a short plain-language reason, for example:

   ```text
   Auto suggests reasoning — unknown-root-cause auth debugging needs investigation. Confirm to run, or override: fast, standard, reasoning, or max.
   ```

5. **Wait for confirmation or override.** Accept a clear confirmation (`confirm`, `yes`, or equivalent) or a tier/model choice. Do not silently change the user's selected model. If the host cannot pause, return the suggestion and let the user's next instruction authorize the run.
6. **Map the tier through the host adapter** described below, then run only after confirmation or an explicit override.
7. **Escalate when needed.** If a light attempt fails or clearly needs more judgment, say once that you are escalating and continue toward `reasoning` or `max` as appropriate.

## Tier rubric

| Tier | Use when |
| --- | --- |
| **fast** | Clear, bounded, low-judgment work: rename, format, short factual answer, simple procedure, or short summary. |
| **standard** | Multi-file edits, known patterns, routine features, or moderate debugging with useful clues. |
| **reasoning** | Ambiguous requirements, unknown-root-cause debugging, architecture, tradeoffs, or security-sensitive work. |
| **max** | Research-level work, formal proofs, large ambiguous redesigns, open-ended invention, or the hardest judgment. |

### Routing guardrails

- When signals conflict and the task is reversible (draft, prototype, dry run, easy undo), prefer the lighter tier.
- Never under-provision security-sensitive work, secrets/authentication work, purchases, sends, or other irreversible external actions; these are at least `reasoning` unless the user explicitly overrides.
- A failed or clearly insufficient light attempt is a reason to escalate, not to keep retrying at the same tier.
- Keep the user-facing explanation to the short suggestion line unless they ask for routing details.

## Adapters

Adapters translate the neutral tier into the controls exposed by each host. They must preserve the same suggest → confirm/override → run flow; they do not silently dispatch.

- **Grok Bot:** map `fast` to low effort; map `standard`, `reasoning`, and `max` to high effort when only low/high controls exist. Keep the four-tier suggestion visible even when the host collapses tiers.
- **Cursor:** use the Cursor model picker (and any available effort control) to select the configured model mapped to the confirmed tier. Ask for confirmation in the conversation before invoking the picker or running the edit.
- **Claude:** select the configured Claude model or effort setting mapped to the confirmed tier. A project may map tiers to its available Claude models; the skill does not require or assume specific model names.
- **Codex:** select the configured Codex model and/or reasoning effort mapped to the confirmed tier. Put this policy in `AGENTS.md`, project instructions, or a supported skills folder; do not assume a specific Codex model name.
- **Other agents:** use the host's model, effort, or routing API and document the local mapping. If no control exists, still show the suggestion and ask for confirmation before proceeding.

## Suggestion line shape

```text
Auto suggests <tier> — <short reason>. Confirm to run, or override: fast, standard, reasoning, or max.
```

## Anti-patterns

- Do not silently pick and run when Auto is user-visible.
- Do not send every clear rename or procedure to `reasoning`/`max` merely to be safe.
- Do not stay at `fast` after a failed attempt that needs judgment.
- Do not ignore an explicit model, provider, effort, or tier choice.
- Do not present heuristic output as a production-quality classifier or as an official vendor recommendation.

## Optional local usage log (consent-gated)

After a confirmed run (or a policy auto-continue, when boundary gates are on), a host **may** append one JSON object per run to `.auto-model-router/usage.jsonl` **only when** `auditOptIn` is `true` in `~/.auto-model-router/config.json` (or a project `.auto-model-router/config.json`). If the flag is missing or false, do not write the log. This is the optional connection used by [`demo/savings_estimator.py`](https://github.com/1ststepai/auto-model-router/blob/main/demo/savings_estimator.py) and Savings Desk (`scripts/audit_usage.py`); it does not call or scrape Cursor, Claude Code, Codex, Gemini, or any billing API.

Minimum schema (one object per line):

```json
{"timestamp":"2026-09-20T13:00:00Z","tier":"standard","confirmed":true,"overridden":false}
```

Required fields are `timestamp` (ISO 8601), `tier` (`fast`, `standard`, `reasoning`, or `max`), `confirmed` (boolean), and `overridden` (boolean). Optional fields include `suggested_tier`, `host`, a non-sensitive `task_kind`, and `gate` (`auto_continue`, `confirm`, or `hard_gate`). For auto-continue, `confirmed` may be `true` (policy-authorized) when `gate` is `auto_continue`.

**Collected when opted in:** timestamp, tier, suggested_tier, confirmed, overridden, host, task_kind, gate.

**Never collect:** prompts, task text, code, secrets, customer data, provider credentials, or anything from a vendor billing/quota API.

The log is local project data and should only be committed if the project explicitly wants to share an anonymized sample.

## On apply / first use

SKILL.md cannot magically open a GUI when Cursor or Claude merely loads a skill — no host hook exists for that. Prefer the apply scripts (`scripts/apply.sh` / `scripts/apply.ps1`) so install copies the demo and opens the savings dashboard by default. Users may disable auto-open with `./scripts/apply.sh --no-open` or `.\scripts\apply.ps1 -NoOpen` (preference saved in `~/.auto-model-router/config.json` as `openDashboardOnApply`); re-enable with `--open` / `-Open`.

Config shape:

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

Weekly review and the usage audit are **opt-in** (`--enable-weekly-review`, `--enable-audit`); they never run unless enabled or `--force` is passed. Empty `usageLogPath` means `~/.auto-model-router/logs/usage.jsonl`.

When the user just installed the skill, says they applied it, or asks to apply / show the savings dashboard:

1. Tell them the dashboard lives at `~/.auto-model-router/demo/dashboard.html` (Windows: `%USERPROFILE%\.auto-model-router\demo\dashboard.html`), or at `demo/dashboard.html` in this repo if they have not run apply yet.
2. If the host allows a shell command, open it with the platform opener (`open` on macOS, `xdg-open` on Linux, `Start-Process` / `Invoke-Item` on Windows) unless they opted out via `--no-open` / config. If a shell is not allowed, give the path and ask them to open it locally.
3. One-line sample: click **Load sample log** in the dashboard (or open `demo/sample_usage_log.json` / `~/.auto-model-router/demo/sample_usage_log.json`) to see illustrative estimates — not live vendor billing.

Do not claim the skill auto-opened a browser just because it was loaded; only claim that after the apply script or an explicit open command succeeded.

## Weekly review (opt-in)

If `weeklyReview` is `true` in `~/.auto-model-router/config.json`, or the user asks what the router did this week / for a weekly summary:

1. Run `python3 ~/.auto-model-router/weekly_review.py` (or `python3 scripts/weekly_review.py --force` from a clone). Use `--force` when the preference is off but the user explicitly asked.
2. Summarize the printed report honestly: it covers the **local** `usage.jsonl` only (tier counts, confirms/overrides, relative-unit estimates). It is **not** live Cursor/Claude/Codex billing.
3. If the log is empty, say so; the script may show the sample log format — label that as sample, not the user's history.
4. Do not install cron/Task Scheduler jobs unless the user explicitly asks; point them at `--install-schedule` / `-InstallSchedule` or the cron examples in INSTALL.md.

## Savings Desk (opt-in audit → automation)

If the user opted in (`auditOptIn=true`) or asks to audit usage / show Savings Desk, follow this order — do not lead with a paid upsell or apply automation unprompted:

1. Detect the active model. Ask which host/picker they are on, or run `python3 scripts/detect_active.py` (`--current-tier`, `--current-model`, `--host`). Live Cursor/Claude/OpenAI pickers and meters cannot be read; use declared values or the latest local `usage.jsonl` row.
2. Audit that pick first: `python3 ~/.auto-model-router/audit_usage.py` (or `python3 scripts/audit_usage.py --force`). Summarize the active host’s burn, then the rest of the local log. Label sample-log fallbacks as sample.
3. Ask “Optimize this?” (boundary-gated confirms, local tier→model map, weekly digest). Only if they say yes, run `python3 scripts/apply_recommendations.py --yes`.
4. Point at `demo/dashboard.html` for the same sequence. Do not lead with a Pro panel.

See [`docs/SAVINGS_DESK.md`](https://github.com/1ststepai/auto-model-router/blob/main/docs/SAVINGS_DESK.md) and [`docs/STACK.md`](https://github.com/1ststepai/auto-model-router/blob/main/docs/STACK.md). Context-lean peers (lean.ctx, ponytail, or any packer) stay optional; a host-neutral checklist is `scripts/context_budget_checklist.md`.

## Honesty

This is a transparent heuristic rubric, not trained routing ML. The reusable product contract is: **context → classify → suggest → confirm/override → run the lightest sufficient option → escalate on failure**.

AMR does not read Cursor, Claude Code, Codex, or Gemini usage/quota/billing APIs. Optional local `usage.jsonl` plus the dashboard are estimates only.

For human installation instructions, see [`INSTALL.md`](https://github.com/1ststepai/auto-model-router/blob/main/INSTALL.md).
