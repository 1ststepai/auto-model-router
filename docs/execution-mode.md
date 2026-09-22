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

`demo/classify.py` imports `MODE_STEERING_PATTERNS`, `MODE_CLOUD_PATTERNS`, and `decide_mode` from `demo/mode.py`, matches them after the escalation signals, and calls `decide_mode` after `decide_gate`.

Helper: `python3 demo/classify.py --examples`
