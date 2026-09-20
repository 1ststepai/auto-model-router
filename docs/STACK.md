# Usage-discipline stack

Three separate layers. None of them is a vendor billing API, and none is bundled IP of the others.

| Layer | Job | This repo |
| --- | --- | --- |
| **AMR** | Model / effort discipline: classify → suggest → (boundary-gated) confirm → run the lightest sufficient tier | Portable skill + host adapters |
| **Context lean tools** | Send less context so every tier costs less | Optional peers — not shipped here |
| **Savings Desk** | Opt-in local audit + one-command policy automation from those logs | `scripts/audit_usage.py`, `scripts/apply_recommendations.py`, `demo/dashboard.html` |

## AMR — model/effort discipline

Auto Model Router is a readable heuristic skill for Cursor, Claude Code, Codex, and Gemini-style agents. It does **not** replace native Auto pickers, scrape usage meters, or guarantee savings. Confirm (or auto-continue, when boundary gates are on) still happens in the host conversation.

See [`SKILL.md`](../SKILL.md) and [`docs/boundary-gated-confirms.md`](boundary-gated-confirms.md).

## Context lean tools — send less context

Tools such as **lean.ctx** and **ponytail** reduce how much context you send. They are complementary peers, not competitors, and this project is **not affiliated** with them. AMR does not shrink context; those tools do not choose a model tier.

A host-neutral pairing checklist lives at [`scripts/context_budget_checklist.md`](../scripts/context_budget_checklist.md). Use it as a reminder, not a vendor lock-in.

## Savings Desk — audit + automate AMR policy

If you **opt in** (`auditOptIn` in `~/.auto-model-router/config.json`), agents may append a non-sensitive line to `usage.jsonl`. Savings Desk then:

1. Reports burns by host, confirm/override rates, heavy-tier use on likely-light `task_kind`s, and relative units vs always-max.
2. Applies local recommendations: `cursor-tier-map.json` plus Claude/Codex stubs, `boundaryGatedConfirms=true`, optional weekly digest.

Relative savings come from that local log first. Optional invoice/CSV reconcile is a later, paid-desk idea — not in this MVP, and never a silent vendor scrape.

See [`docs/SAVINGS_DESK.md`](SAVINGS_DESK.md).
