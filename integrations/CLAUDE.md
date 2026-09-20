# Claude integration

## Install

For a project-local Claude Code setup:

```bash
mkdir -p .claude/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md
```

You can instead paste the skill into `CLAUDE.md` or include it from project instructions using the instruction mechanism supported by your Claude setup. A user-level copy can be installed in the user skills/instructions location supported by Claude Code.

## Wire suggest → confirm

1. Classify the request using the neutral four-tier rubric.
2. Tell the user the suggested tier and short reason before starting model work.
3. Wait for `confirm` or an explicit tier/model override.
4. Select the configured Claude model or effort setting for that tier, then run.
5. After a failed light attempt, state that you are escalating and continue with a stronger configured model/effort.

Do not bake specific Claude model names into the portable skill; map the tiers to the models enabled for the project.
