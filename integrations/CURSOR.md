# Cursor integration

## Install

From a project containing this repository:

```bash
mkdir -p .cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md
```

For a user-wide setup, copy the same file into the user skills directory supported by your Cursor installation. Another option is to link or reference the canonical file from a `.cursor/rules/` rule. Keep the rule short and point it at `skills/auto-model-router/SKILL.md` so the policy remains portable.

## Wire suggest → confirm

1. Before a model-dependent task, assess context and classify it as `fast`, `standard`, `reasoning`, or `max`.
2. Show `Auto suggests <tier> — <reason>. Confirm to run, or override...` in chat.
3. Wait for the user's confirmation or model/tier override.
4. Use Cursor's model picker and available effort controls to map the confirmed tier, then run.
5. If the attempt is clearly too light, explain the escalation once and select a stronger configured option.

Cursor's model names change over time, so keep the mapping local to the project's available picker rather than hard-coding vendor names in the skill.
