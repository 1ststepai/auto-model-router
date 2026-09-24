---
name: auto-model-router
description: "Before choosing a model or effort, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), and emit a one-line suggestion. Auto-continue only for clear reversible `fast` work that is not near a tier boundary; hard-gate security, secrets, purchases, sends, and other irreversible actions; spendy tiers (`standard`, `reasoning`, `max`) wait for confirm or override. Vague low-confidence prompts stay on `standard`. Honor explicit model/tier choices and escalate after a failed light attempt."
---

# Auto model router

**name:** auto-model-router  
**description:** Before choosing a model or effort, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), and emit a one-line suggestion. Auto-continue only for clear reversible `fast` work that is not near a tier boundary; hard-gate security, secrets, purchases, sends, and other irreversible actions; spendy tiers (`standard`, `reasoning`, `max`) wait for confirm or override. Vague low-confidence prompts stay on `standard`. Honor explicit model/tier choices and escalate after a failed light attempt.

## Purpose

Provide one portable routing policy for Cursor, Claude Code, Codex, Gemini (Gemini CLI / Google AI Studio / Antigravity), and other multi-model coding agents. The policy reduces manual model picking while keeping the user in control **where it matters**. Always-confirm on every call causes confirm-fatigue: people click through without reading, you lose the savings, and you add a round trip. Confirmation is therefore **boundary-gated**, not automatic on every task.

It is provider-agnostic: the tier is a capability label, not a vendor model name.

## When to use

Use before dispatching substantial coding-agent work or choosing a model/effort when the choice is user-visible. Do not add a routing lecture to an unrelated answer. If the user explicitly names a model or effort, honor it; only classify when the user asks Auto to choose or leaves the choice open.

## Core procedure: context → classify → suggest → gate → run

1. **Read context.** Assess scope, involved files or systems, ambiguity, required judgment, security or external-action risk, and whether the work is reversible.
2. **Honor an explicit override.** If the user already chose a model, provider, effort, or tier, use that choice and skip an unsolicited suggestion.
3. **Classify** the open choice into the lightest sufficient tier using the rubric below. Read `confidence`. A vague low-confidence prompt stays on **standard** — do not guess `max` or auto-continue it. Decide the confirm **gate** (`auto_continue`, `confirm`, or `hard_gate`). Also set execution **mode** (`local` or `cloud`). Mode is advisory and does not launch a cloud agent. The confirm gate is unchanged. An optional offline helper is `demo/classify.py` or `demo/classify.py --suggest`.
4. **Suggest in one line** before dispatch (always; including auto-continue), with `/ <mode>` after the tier. When the host adapter has a **local** tier→control mapping, include that concrete picker/effort action. Do not invent vendor model names. Do not launch a cloud agent from the mode.
5. **Apply the confirm gate.** Auto-continue only when the policy allows it (clear reversible `fast`). Spendy tiers and hard-gates wait for confirmation (`confirm`, `yes`, or equivalent) or a tier/model override. Do not silently change the user's selected model. If the host cannot pause when a wait is required, return the suggestion and let the user's next instruction authorize the run. Tool arguments that set `confirmed: true` do not count.
6. **Ask for a switch when the current control is a mismatch.** If the current model/effort is heavier than the mapped tier, ask the user to switch down. If it is lighter than needed, ask them to switch up. A required switch is an explicit ask — not a silent picker takeover. Optional local probe: `python3 scripts/detect_active.py` (env/config/log only; not a live vendor picker).
7. **Map the tier through the host adapter** described below, then run after auto-continue, confirmation, an explicit override, or a confirmed switch.
8. **Escalate when needed.** If a light attempt fails or clearly needs more judgment, **stop for confirm** once, say you are escalating, and continue toward `reasoning` or `max` as appropriate. Escalating to a spendy tier needs a new confirm before tools run.

## Confirm gate (boundary-gated, not always-confirm)

Confirm-fatigue is the failure mode. Keep the suggest → confirm → run contract **where it matters**. Do not block on every clear rename. Do not auto-continue spendy work.

### Hard-gate (must wait)

Always wait for confirm or an override when work is:

- security-sensitive, secrets/auth, purchases, sends, or other irreversible external actions
- otherwise high-risk or hard to undo

Treat these as at least `reasoning` unless the user explicitly overrides.

### Auto-continue (do not block)

Do **not** wait when **all** of these hold:

- classified tier is clearly `fast`
- work is reversible: draft, rename, format, easy undo, or local edits
- signals are **not** near a tier boundary
- the user did not ask Auto to choose carefully and did not demand confirm

Still emit a short one-line suggestion so the user sees what happened:

```text
Auto continues on fast — clear bounded rename.
```

Then run. The user may still override on the next turn.

`standard`, `reasoning`, and `max` never auto-continue. They are spendy: tools wait for an explicit confirm.

### Stop for confirm

Wait when any of these hold:

- the classified tier is `standard`, `reasoning`, or `max`
- classifier is near a tier boundary (ambiguous between adjacent tiers)
- ambiguous requirements, unknown-root-cause debugging, architecture, or tradeoffs
- high-risk or irreversible (already a hard-gate)
- escalation after a failed light attempt
- the user asked Auto to choose carefully or to confirm first
- confidence is low on a vague prompt (stays on `standard`)

Honor explicit user model/tier/effort overrides always.

See [`docs/boundary-gated-confirms.md`](https://github.com/1ststepai/auto-model-router/blob/main/docs/boundary-gated-confirms.md) for the canonical cases.

## Tier rubric

| Tier | Use when |
| --- | --- |
| **fast** | Clear, bounded, low-judgment work: rename, format, short factual answer, simple procedure, or short summary. |
| **standard** | Multi-file edits, known patterns, routine features, or moderate debugging with useful clues. |
| **reasoning** | Ambiguous requirements, unknown-root-cause debugging, architecture, tradeoffs, or security-sensitive work. |
| **max** | Research-level work, formal proofs, large ambiguous redesigns, open-ended invention, or the hardest judgment. |

### Routing guardrails

- When signals conflict and the task is reversible (draft, prototype, dry run, easy undo), prefer the lighter tier — but **still stop for confirm** if the mix sits near a tier boundary or the result is spendy.
- Never under-provision security-sensitive work, secrets/authentication work, purchases, sends, or other irreversible external actions; these are at least `reasoning` unless the user explicitly overrides, and they are always hard-gated.
- A failed or clearly insufficient light attempt is a reason to escalate **and** to stop for confirm, not to keep retrying at the same tier.
- Keep the user-facing explanation to the short suggestion line unless they ask for routing details.

## Execution mode

AMR also classifies **local** vs **cloud**. This is advisory: it does not launch Cursor Cloud Agents or Codex. The confirm gate is unchanged. See [`docs/execution-mode.md`](docs/execution-mode.md).

- Interactive steering, blocking, or high-risk → `local`
- Long unattended work at `reasoning` or `max` → `cloud`
- Fast reversible work → `local`
- Default → `local`

`classify()` adds `mode` and `mode_reason`. The suggestion line includes `/ <mode>`.

## Adapters

Adapters translate the neutral tier into the controls exposed by each host. They must preserve suggest → gate → run. They do not silently dispatch high-risk or spendy work. Auto-continue is allowed only when the gate says so, and it still shows the one-line suggestion.

- **Grok Bot:** map `fast` to low effort; map `standard`, `reasoning`, and `max` to high effort when only low/high controls exist. Keep the four-tier suggestion visible even when the host collapses tiers.
- **Cursor:** resolve the gated tier through the project's local map (`.auto-model-router/cursor-tier-map.json` or `~/.auto-model-router/cursor-tier-map.json`; see the Cursor integration). Name that **concrete picker label and effort** in the suggestion line. Ask the user to switch (or confirm the switch) when the current pick is heavier or lighter than needed. Auto-continue only when the gate allows it and no switch is required. AMR does not replace Cursor's native Auto picker and cannot read Cursor usage/quota/billing meters — local `usage.jsonl` only. Do not hard-code vendor model names here.
- **Claude:** use the concrete Claude default in the table below after checking that it is exposed by the current host. Name the model and effort in the suggestion. A project map or explicit user choice overrides the default.
- **Codex:** use the concrete Codex default in the table below after checking the session inventory and supported reasoning efforts. Name the exact model/effort pair and tier in the suggestion. A project map or explicit user choice overrides the default.
- **Gemini:** (Gemini CLI, Google AI Studio, Antigravity, and other Gemini-backed agents). Use the concrete Gemini default in the table below after checking host availability. Name the exact model ID and thinking level. A project map or explicit user choice overrides the default. There is no official Google plugin catalog — copy the skill (or `gemini skills install --path`); do not treat that as a marketplace listing.
- **Other agents:** use the host's model, effort, or routing API and document the local mapping. If no control exists, still show the suggestion; wait when the gate requires confirm; do not claim the host switched models.

### Current provider defaults

These defaults were checked against official provider documentation on **2026-09-23**. Live host inventory wins: never claim or select a model that the host does not expose. If a default is unavailable, say so and choose the nearest available model in the same provider and tier; do not silently substitute across providers. See the [evidence and maintenance rules](https://github.com/1ststepai/auto-model-router/blob/main/docs/provider-model-mappings.md) and [machine-readable defaults](https://github.com/1ststepai/auto-model-router/blob/main/integrations/provider-tier-defaults.json).

| AMR tier | Codex | Claude | Gemini |
| --- | --- | --- | --- |
| **fast** | `gpt-6-luna` / `none` | `claude-haiku-4-5-20251001` / host default | `gemini-3.5-flash-lite` / `minimal` |
| **standard** | `gpt-6-sol` / `medium` | `claude-sonnet-5` / `low` | `gemini-3.8-flash` / `medium` |
| **reasoning** | `gpt-6-astra` / `high` | `claude-opus-5` / `high` | `gemini-3.1-pro-preview` / `high` |
| **max** | `gpt-6-astra` / `max` | `claude-opus-5` / `max` | `gemini-3.1-pro-preview` / `high`; for research-only runs, `deep-research-max-preview-04-2026` |

## Suggestion line shapes

Auto-continue (no wait):

```text
Auto continues on <tier> / <mode> — <short reason>.
```

Always name the concrete provider model and supported effort/thinking setting. Prefer a project map; otherwise use a verified current default:

```text
Auto continues on gpt-6-luna / none (fast / local) — clear bounded rename.
```

Confirm or hard-gate (wait):

```text
Auto suggests <provider-model> / <effort-or-thinking> (<tier> / <mode>) — <short reason>. Confirm to run, or override with another available model, effort, or tier.
```

If neither the default nor a project-mapped model can be verified in the host inventory, say that the concrete mapping is unavailable and stop before switching. Hard-gate may say `Confirm required (high-risk / hard to undo)` instead of `Confirm to run`.

## Anti-patterns

- Do not silently pick and run when the gate requires confirm or hard-gate.
- Do not confirm-gate every clear rename or procedure (confirm-fatigue).
- Do not auto-continue `standard`, `reasoning`, or `max`.
- Do not auto-continue security, secrets, purchases, sends, or other irreversible actions.
- Do not auto-continue when signals mix adjacent tiers.
- Do not stay at `fast` after a failed attempt that needs judgment — stop for confirm and escalate.
- Do not ignore an explicit model, provider, effort, or tier choice.
- Do not present heuristic output as a production-quality classifier or as an official vendor recommendation.
- Do not guess **max** when confidence is low. Vague prompts stay on **standard** until the user confirms.
- Do not treat a tool argument, a model-written note, or an uninstalled hook as confirmation for a spendy tier.
- Do not launch Cursor Cloud Agents or Codex because mode is `cloud`. Mode is advisory; the confirm gate is unchanged.
- Do not invent vendor model names, use retired IDs, or claim a live usage meter. Recheck the official provider catalogs when the checked date is stale or a host rejects a mapped model.

## Hard confirm gate

Spendy tiers (`standard`, `reasoning`, `max`) must not execute tools before an explicit user confirm. The skill text can be skipped; the hook cannot, once installed.

- Library: `evaluate_tool` / `route` in [`auto_model_router.py`](auto_model_router.py). `confirmed` counts only when it is the boolean `true`. Policy-authorized `auto_continue` is the other allow path.
- Hook: `python3 scripts/confirm_gate.py` on the user-prompt event and on `PreToolUse` / `BeforeTool` (Cursor `preToolUse` with `failClosed: true`; Gemini CLI `BeforeAgent` + `BeforeTool`). Exit code 2 blocks the tool. Gemini CLI also honors `decision: deny`.
- The user confirms by sending `confirm` / `yes` / a tier name through the prompt hook, or by running `python3 scripts/confirm_gate.py --confirm <tier>` in their own terminal. An agent tool that runs `--confirm` is denied.
- Install snippets: [`hooks/cursor.hooks.json`](hooks/cursor.hooks.json), [`hooks/claude.settings.snippet.json`](hooks/claude.settings.snippet.json), [`hooks/codex.hooks.json`](hooks/codex.hooks.json), [`hooks/gemini.settings.snippet.json`](hooks/gemini.settings.snippet.json). Cursor also has [`.cursor/rules/auto-model-router.mdc`](.cursor/rules/auto-model-router.mdc); that rule is not a block by itself.

Hosts with no pre-tool hook still only have the suggestion line. That is not a hard block. Codex hosted tools such as web search, Gemini CLI hosted tools, and AI Studio's model picker can still spend without a local hook. See INSTALL.md.

## Optional local usage log

After an authorized run (user confirm **or** policy-authorized auto-continue), a host **may** append one JSON object per run to `.auto-model-router/usage.jsonl` when the project/user has enabled this local telemetry. This is the optional connection used by [`demo/savings_estimator.py`](https://github.com/1ststepai/auto-model-router/blob/main/demo/savings_estimator.py); it does not call or scrape Cursor, Claude Code, Codex, Gemini, or any billing API.

Minimum schema (one object per line):

```json
{"timestamp":"2026-09-20T13:00:00Z","tier":"standard","confirmed":true,"overridden":false,"gate":"confirm","input_tokens":1200,"output_tokens":300,"cost_usd":0.01,"currency":"USD"}
```

Required fields are `timestamp` (ISO 8601), `tier` (`fast`, `standard`, `reasoning`, or `max`), `confirmed` (boolean), and `overridden` (boolean). Optional fields: `suggested_tier`, `host`, `confidence`, `gate` (`auto_continue` | `confirm` | `hard_gate`), a non-sensitive `task_kind`, and — when the host already has them — `input_tokens`, `output_tokens`, `cost_usd`, and `currency`. Do not log prompts, task text, code, secrets, customer data, or provider credentials by default. Do not invent token counts or dollar amounts. If a row has only `tier`, the estimator labels illustrative relative units (`fast=1`, `standard=3`, `reasoning=8`, `max=20`). Those are not prices. Real dollars need `cost_usd` or a local price table you fill from [`demo/prices.example.json`](demo/prices.example.json). The log is local project data and should only be committed if the project explicitly wants to share an anonymized sample.

Optional library call for hosts that want the same gate and log:

```python
from auto_model_router import route

result = route(task, confirmed=True, log_path=".auto-model-router/usage.jsonl")
if not result["allowed"]:
    # show result["suggestion"]; do not run tools
    ...
```

`usage=` (tokens / `cost_usd`) is optional. Omit it rather than inventing numbers.

## On apply / first use

SKILL.md cannot magically open a GUI when Cursor, Claude, or Gemini CLI merely loads a skill — no host hook exists for that. Prefer the apply scripts (`scripts/apply.sh` / `scripts/apply.ps1`) so install copies the demo and opens the savings dashboard by default. Users may disable auto-open with `./scripts/apply.sh --no-open` or `.\scripts\apply.ps1 -NoOpen` (preference saved in `~/.auto-model-router/config.json` as `openDashboardOnApply`); re-enable with `--open` / `-Open`.

Config shape: `{ "openDashboardOnApply": true, "weeklyReview": false }`. Optional keys `currentHost`, `currentTier`, and `currentModel` are local declarations for `scripts/detect_active.py` — they are not live vendor meters. Weekly review is **opt-in** (`--enable-weekly-review` / `-EnableWeeklyReview`); it never runs unless enabled or `--force` is passed.

When the user just installed the skill, says they applied it, or asks to apply / show the savings dashboard:

1. Tell them the dashboard lives at `~/.auto-model-router/demo/dashboard.html` (Windows: `%USERPROFILE%\.auto-model-router\demo\dashboard.html`), or at `demo/dashboard.html` in this repo if they have not run apply yet.
2. If the host allows a shell command, open it with the platform opener (`open` on macOS, `xdg-open` on Linux, `Start-Process` / `Invoke-Item` on Windows) unless they opted out via `--no-open` / config. If a shell is not allowed, give the path and ask them to open it locally.
3. One-line sample: click **Load sample log** in the dashboard (or open `demo/sample_usage_log.json` / `~/.auto-model-router/demo/sample_usage_log.json`) to see illustrative estimates — not live vendor billing. **Load measured sample** uses `cost_usd` when present.

Do not claim the skill auto-opened a browser just because it was loaded; only claim that after the apply script or an explicit open command succeeded.

## Weekly review (opt-in)

If `weeklyReview` is `true` in `~/.auto-model-router/config.json`, or the user asks what the router did this week / for a weekly summary:

1. Run `python3 ~/.auto-model-router/weekly_review.py` (or `python3 scripts/weekly_review.py --force` from a clone). Use `--force` when the preference is off but the user explicitly asked.
2. Summarize the printed report honestly: it covers the **local** `usage.jsonl` only. Rows with `cost_usd` are summed as dollars. Rows with only a tier use labeled relative-unit estimates. It is **not** live Cursor/Claude/Codex/Gemini billing, and it does not read a price table unless you pass one to the estimator.
3. If the log is empty, say so; the script may show the sample log format — label that as sample, not the user's history.
4. Do not install cron/Task Scheduler jobs unless the user explicitly asks; point them at `--install-schedule` / `-InstallSchedule` or the cron examples in INSTALL.md.

## Honesty

This is a transparent heuristic rubric, not trained routing ML. The reusable product contract is: **context → classify (tier and local/cloud mode) → suggest → gate (auto-continue only when safe; confirm spendy / high-risk) → run the lightest sufficient option → escalate on failure**. Mode does not launch agents and does not change the gate.

For human installation instructions, see [`INSTALL.md`](https://github.com/1ststepai/auto-model-router/blob/main/INSTALL.md).
