# Codex integration

## Install

Add the skill to project instructions, commonly `AGENTS.md`:

```bash
cat skills/auto-model-router/SKILL.md >> AGENTS.md
```

If your Codex setup supports skills, copy it into the supported skills directory instead. A marked, referenced section is preferable when `AGENTS.md` already contains other project policy.

## Wire suggest → confirm

1. Read task context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Present the suggestion and one-line reason to the user.
3. Wait for confirmation or a tier/model/effort override before dispatch.
4. Map the confirmed tier to the Codex model and/or reasoning effort configured for the project, then run.
5. Escalate toward `reasoning` or `max` after an insufficient light attempt and explain the change once.

Tier labels are deliberately not Codex product names. Keep the mapping in project instructions so it can evolve with the available Codex models.
