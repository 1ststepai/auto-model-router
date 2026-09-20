---
name: auto-model-router
description: "Before choosing a model or effort, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), and emit a one-line suggestion. Auto-continue only for clear reversible `fast` (or strongly fitting `standard`) work that is not near a tier boundary; hard-gate security, secrets, purchases, sends, and other irreversible actions; otherwise wait for confirm or override. Honor explicit model/tier choices and escalate after a failed light attempt."
---

# Auto model router

**name:** auto-model-router  
**description:** Before choosing a model or effort, read the task context, classify it into the lightest sufficient tier (`fast`, `standard`, `reasoning`, or `max`), and emit a one-line suggestion. Auto-continue only for clear reversible `fast` (or strongly fitting `standard`) work that is not near a tier boundary; hard-gate security, secrets, purchases, sends, and other irreversible actions; otherwise wait for confirm or override. Honor explicit model/tier choices and escalate after a failed light attempt.

## Purpose

Provide one portable routing policy for Cursor, Claude, Codex, and other multi-model coding agents. The policy reduces manual model picking while keeping the user in control **where it matters**. Always-confirm on every call causes confirm-fatigue: people click through without reading, you lose the savings, and you add a round trip. Confirmation is therefore **boundary-gated**, not automatic on every task.

It is provider-agnostic: the tier is a capability label, not a vendor model name.

## When to use

Use before dispatching substantial coding-agent work or choosing a model/effort when the choice is user-visible. Do not add a routing lecture to an unrelated answer. If the user explicitly names a model or effort, honor it; only classify when the user asks Auto to choose or leaves the choice open.

## Core procedure: context → classify → suggest → gate → run

1. **Read context.** Assess scope, involved files or systems, ambiguity, required judgment, security or external-action risk, and whether the work is reversible.
2. **Honor an explicit override.** If the user already chose a model, provider, effort, or tier, use that choice and skip an unsolicited suggestion.
3. **Classify** the open choice into the lightest sufficient tier using the rubric below. Decide the confirm **gate** (`auto_continue`, `confirm`, or `hard_gate`) using the policy in the next section. An optional offline helper is `demo/classify.py` or `demo/classify.py --suggest`; it is only a heuristic second opinion and may emit `near_boundary`, `high_risk`, `reversible`, and `gate`.
4. **Suggest in one line** before dispatch (always; including auto-continue). Use the shapes below.
5. **Apply the confirm gate.** Auto-continue only when the policy allows it. Otherwise wait for confirmation (`confirm`, `yes`, or equivalent) or a tier/model override. Do not silently change the user's selected model. If the host cannot pause when a wait is required, return the suggestion and let the user's next instruction authorize the run.
6. **Map the tier through the host adapter** described below, then run after auto-continue, confirmation, or an explicit override.
7. **Escalate when needed.** If a light attempt fails or clearly needs more judgment, **stop for confirm** once, say you are escalating, and continue toward `reasoning` or `max` as appropriate.

## Confirm gate (boundary-gated, not always-confirm)

Confirm-fatigue is the failure mode. Keep the suggest → confirm → run contract **where it matters**. Do not block on every clear rename.

### Hard-gate (must wait)

Always wait for confirm or an override when work is:

- security-sensitive, secrets/auth, purchases, sends, or other irreversible external actions
- otherwise high-risk or hard to undo

Treat these as at least `reasoning` unless the user explicitly overrides.

### Auto-continue (do not block)

Do **not** wait when **all** of these hold:

- classified tier is clearly `fast`, or clearly `standard` with strong rubric fit (only standard-family signals, not mixed, solid confidence)
- work is reversible: draft, rename, format, easy undo, or local edits
- signals are **not** near a tier boundary (no ambiguity between adjacent tiers; no mixed-family decision)
- the user did not ask Auto to choose carefully and did not demand confirm

Still emit a short one-line suggestion so the user sees what happened:

```text
Auto continues on fast — clear bounded rename.
```

Then run. The user may still override on the next turn.

### Stop for confirm

Wait when any of these hold:

- classifier is near a tier boundary (ambiguous between adjacent tiers)
- ambiguous requirements, unknown-root-cause debugging, architecture, or tradeoffs
- high-risk or irreversible (already a hard-gate)
- escalation after a failed light attempt
- the user asked Auto to choose carefully or to confirm first

Honor explicit user model/tier/effort overrides always.

See [`docs/boundary-gated-confirms.md`](https://github.com/1ststepai/auto-model-router/blob/main/docs/boundary-gated-confirms.md) for the three canonical cases.

## Tier rubric

| Tier | Use when |
| --- | --- |
| **fast** | Clear, bounded, low-judgment work: rename, format, short factual answer, simple procedure, or short summary. |
| **standard** | Multi-file edits, known patterns, routine features, or moderate debugging with useful clues. |
| **reasoning** | Ambiguous requirements, unknown-root-cause debugging, architecture, tradeoffs, or security-sensitive work. |
| **max** | Research-level work, formal proofs, large ambiguous redesigns, open-ended invention, or the hardest judgment. |

### Routing guardrails

- When signals conflict and the task is reversible (draft, prototype, dry run, easy undo), prefer the lighter tier — but **still stop for confirm** if the mix sits near a tier boundary.
- Never under-provision security-sensitive work, secrets/authentication work, purchases, sends, or other irreversible external actions; these are at least `reasoning` unless the user explicitly overrides, and they are always hard-gated.
- A failed or clearly insufficient light attempt is a reason to escalate **and** to stop for confirm, not to keep retrying at the same tier.
- Keep the user-facing explanation to the short suggestion line unless they ask for routing details.

## Adapters

Adapters translate the neutral tier into the controls exposed by each host. They must preserve suggest → gate → run. They do not silently dispatch high-risk or ambiguous work. Auto-continue is allowed only when the gate says so, and it still shows the one-line suggestion.

- **Grok Bot:** map `fast` to low effort; map `standard`, `reasoning`, and `max` to high effort when only low/high controls exist. Keep the four-tier suggestion visible even when the host collapses tiers.
- **Cursor:** use the Cursor model picker (and any available effort control) to select the configured model mapped to the gated tier. Auto-continue only when the gate allows it; otherwise ask for confirmation in the conversation before invoking the picker or running the edit.
- **Claude:** select the configured Claude model or effort setting mapped to the gated tier. A project may map tiers to its available Claude models; the skill does not require or assume specific model names.
- **Codex:** select the configured Codex model and/or reasoning effort mapped to the gated tier. Put this policy in `AGENTS.md`, project instructions, or a supported skills folder; do not assume a specific Codex model name.
- **Other agents:** use the host's model, effort, or routing API and document the local mapping. If no control exists, still show the suggestion; wait when the gate requires confirm; do not claim the host switched models.

## Suggestion line shapes

Auto-continue (no wait):

```text
Auto continues on <tier> — <short reason>.
```

Confirm or hard-gate (wait):

```text
Auto suggests <tier> — <short reason>. Confirm to run, or override: fast, standard, reasoning, or max.
```

Hard-gate may say `Confirm required (high-risk / hard to undo)` instead of `Confirm to run`.

## Anti-patterns

- Do not silently pick and run when the gate requires confirm or hard-gate.
- Do not confirm-gate every clear rename or procedure (confirm-fatigue).
- Do not auto-continue security, secrets/auth, purchases, sends, or other irreversible work.
- Do not auto-continue when signals mix adjacent tiers or the root cause is unknown.
- Do not send every clear rename or procedure to `reasoning`/`max` merely to be safe.
- Do not stay at `fast` after a failed attempt that needs judgment — escalate and stop for confirm.
- Do not ignore an explicit model, provider, effort, or tier choice.
- Do not present heuristic output as a production-quality classifier or as an official vendor recommendation.

## Optional local usage log

After an authorized run (user confirm/override **or** policy auto-continue), a host **may** append one JSON object per run to `.auto-model-router/usage.jsonl` when the project/user has enabled this local telemetry. This is the optional connection used by [`demo/savings_estimator.py`](https://github.com/1ststepai/auto-model-router/blob/main/demo/savings_estimator.py); it does not call or scrape Cursor, Claude Code, Codex, or any billing API.

Minimum schema (one object per line):

```json
{"timestamp":"2026-09-20T13:00:00Z","tier":"standard","confirmed":true,"overridden":false}
```

Required fields are `timestamp` (ISO 8601), `tier` (`fast`, `standard`, `reasoning`, or `max`), `confirmed` (boolean), and `overridden` (boolean). Optional fields include `suggested_tier`, `host`, a non-sensitive `task_kind`, and `gate` (`auto_continue`, `confirm`, or `hard_gate`). For auto-continue, `confirmed` may be `true` (policy-authorized) when `gate` is `auto_continue`. Do not log prompts, task text, code, secrets, customer data, or provider credentials by default. The log is local project data and should only be committed if the project explicitly wants to share an anonymized sample.

## On apply / first use

SKILL.md cannot magically open a GUI when Cursor or Claude merely loads a skill — no host hook exists for that. Prefer the apply scripts (`scripts/apply.sh` / `scripts/apply.ps1`) so install copies the demo and opens the savings dashboard by default. Users may disable auto-open with `./scripts/apply.sh --no-open` or `.\scripts\apply.ps1 -NoOpen` (preference saved in `~/.auto-model-router/config.json` as `openDashboardOnApply`); re-enable with `--open` / `-Open`.

Config shape: `{ "openDashboardOnApply": true, "weeklyReview": false }`. Weekly review is **opt-in** (`--enable-weekly-review` / `-EnableWeeklyReview`); it never runs unless enabled or `--force` is passed.

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

## Honesty

This is a transparent heuristic rubric, not trained routing ML. The reusable product contract is: **context → classify → suggest → boundary-gated confirm/override → run the lightest sufficient option → escalate on failure**.

For human installation instructions, see [`INSTALL.md`](https://github.com/1ststepai/auto-model-router/blob/main/INSTALL.md).
