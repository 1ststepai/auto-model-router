# Execution mode

AMR now classifies a second axis: **local** vs **cloud**.

This is advisory. It does not launch Cursor Cloud Agents or Codex. The confirm gate is unchanged.

## Signals

- Interactive steering / blocking / high-risk → `local`
- Long unattended work at `reasoning` or `max` → `cloud`
- Fast reversible work → `local`
- Default → `local`

## Classifier output

`classify()` adds:

```json
{
  "mode": "local",
  "mode_reason": "quick reversible work; local is cheaper"
}
```

Suggestion line shape:

```text
Auto suggests standard / local — multi-file known pattern. Confirm to run…
```

## Apply the remaining wiring

Branch `feat/local-cloud-mode` includes `demo/mode.py`.
Wire it in `demo/classify.py`:

1. Import `MODE_STEERING_PATTERNS`, `MODE_CLOUD_PATTERNS`, and `decide_mode` from `demo.mode`.
2. Match those patterns after the existing escalation signals.
3. Call `decide_mode(...)` after `decide_gate`.
4. Add `mode` and `mode_reason` to the returned dict (including the empty-task case).
5. Include `/ {mode}` in `suggest_line`.

Helper: `python3 demo/classify.py --examples`
