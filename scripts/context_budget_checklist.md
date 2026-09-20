# Context budget checklist (pairs with AMR)

Use this before a substantial coding-agent turn. It is a reminder, not a product lock-in and not part of any vendor’s billing API.

AMR chooses **which tier** to spend. Context lean tools choose **how much** you send. Do both.

## Before you route

- [ ] Can the task be done with the open file + a named symbol, not the whole repo?
- [ ] Drop generated folders, lockfiles, and vendor trees from the attach set.
- [ ] Prefer a failing test / stack trace over “read everything and figure it out.”
- [ ] If you use a context-lean helper (lean.ctx, ponytail, or your own packer), run it **before** the model call — then let AMR classify the remaining ask.
- [ ] Do not paste secrets, `.env`, or credentials into context. AMR will not log them; you still should not send them.

## After AMR suggests a tier

- [ ] If the suggestion is `fast` / `standard` and the context pack is still huge, shrink context first instead of escalating the tier.
- [ ] If the suggestion is `reasoning` / `max`, keep the context tight anyway — heavy tiers waste more on noise.
- [ ] Confirm or override the tier in the host. AMR does not flip Cursor/Claude/Codex Auto for you.

## After the run

- [ ] If `auditOptIn` is on, the host may append `tier`, `host`, `confirmed`/`overridden`, `task_kind` (no prompt text).
- [ ] Heavy tier + light `task_kind` is a Savings Desk switch-down clue, not a bill.

No affiliation with lean.ctx or ponytail is claimed. Swap in any packer you already trust.
