# Boundary-gated confirms

Always-confirm on every Auto routing call looks safe and is not. People click through without reading, you lose the savings, and you add a round trip. Confirm-fatigue is the failure mode.

This note is the policy, not a production router. The portable classifier stays a readable heuristic. Hosts still follow **context → classify → suggest → gate → run**. What changed is **when** confirmation blocks.

Spendy tiers (`standard`, `reasoning`, `max`) **cannot run tools until confirmed**. Fast auto-continues only when the work is clearly reversible, not near a boundary, and not high-risk.

## Three gates

| Gate | When | UX |
| --- | --- | --- |
| **hard_gate** | Security, secrets/auth, purchases, sends, or other irreversible / hard-to-undo work | Must wait for confirm or override |
| **auto_continue** | Clearly `fast`, reversible, not near a tier boundary, user did not demand confirm | One-line notice, then run |
| **confirm** | Any spendy tier, near-boundary signals, ambiguous/unknown-root-cause/architecture, escalation after a failed light attempt, or user asked to wait | Wait for confirm or override |

Explicit user model, effort, or tier choices always win. Vague low-confidence prompts stay on `standard` (never a guessed `max`) and therefore wait.

An optional local hook (`scripts/confirm_gate.py`) can hard-block spendy tool calls. A skill or Cursor rule is not a runtime block by itself. Tool arguments that set `confirmed: true` do not unlock the gate.

## Canonical cases

### Clear rename → auto-continue

```text
User: Rename the variable foo to bar in utils.py
Agent: Auto continues on fast — clear bounded rename. Switch Cursor picker to
       <your-fast-model> / low effort if the current model is heavier than needed.
```

Reversible local edit, only fast-family signals, no boundary ambiguity.

### Auth / secrets → hard-gate

```text
User: Review this auth change for XSS and credential leaks
Agent: Auto suggests reasoning — security-sensitive review must not be under-provisioned.
       Switch Cursor picker to <your-reasoning-model> / high effort (current pick is
       lighter than needed). Confirm the switch, or override: fast, standard, reasoning, or max.
```

Same gate for purchases, customer sends, production deploys, and other irreversible external actions.

### Spendy / near-boundary → confirm

```text
User: Wire up a CRUD endpoint using the existing handler pattern
Agent: Auto suggests standard — multi-file known-pattern work. Confirm to run,
       or override: fast, standard, reasoning, or max.

User: Rename the helper and apply the same null-check pattern across a few files
Agent: Auto suggests standard — mixed rename + multi-file signals sit near a tier boundary.
       Confirm to run, or override: fast, standard, reasoning, or max.
```

`standard` is spendy: it waits even when the fit is strong. Adjacent-tier hits (`fast` + `standard`) also wait.

## Try the heuristic

```bash
python3 demo/classify.py --suggest "Rename the variable foo to bar in utils.py"
python3 demo/classify.py --suggest --map integrations/cursor-tier-map.example.json \
  --current-tier max "Rename the variable foo to bar in utils.py"
python3 demo/classify.py --suggest "Review this auth change for XSS and credential leaks"
python3 demo/classify.py --suggest "Wire up a CRUD endpoint using the existing handler pattern"
python3 demo/classify.py --examples
```

JSON includes `tier`, `gate`, `near_boundary`, `high_risk`, `reversible`, `confidence`, `needs_confirm`, `downshifted_from`, and `signals`. Treat `near_boundary` as a rubric flag (mixed families or a mixed-signal decision), not a learned probability.

## What this is not

- Not a billing API, savings guarantee, or vendor affiliation
- Not a production routing proxy and not a silent takeover of Cursor Auto
- Not a live Cursor/Claude/Codex usage or quota meter
- Not trained ML and not a security control
