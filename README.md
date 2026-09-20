# Portable Auto router for any multi-model coding agent

An open-source, provider-agnostic skill for routing coding-agent work to the lightest model or effort tier that can do it well. It is designed for **Cursor, Claude Code, Codex, and similar multi-model tools**—without requiring any one vendor's API or model names.

**Flow:** context → classify (`fast` / `standard` / `reasoning` / `max`) → suggest → user confirm/override → run.

The repository contains a portable skill, small offline heuristic demo, integration notes, and examples. Copy the skill into each project or add it to your user-level agent instructions so all your projects can use the same routing policy.

## Why use it?

Manual model picking causes both over-provisioning (slow, expensive models for trivial edits) and under-provisioning (weak models for ambiguous, risky, or architectural work). Auto model routing should reduce that choice overhead **without silently changing what runs**:

1. Read the task context: scope, ambiguity, risk, reversibility, and judgment required.
2. Classify it into the lightest sufficient tier: `fast`, `standard`, `reasoning`, or `max`.
3. Suggest the tier and give a short reason.
4. Let the user confirm or override it.
5. Run with the chosen provider/model/effort mapping.
6. Escalate after a clearly insufficient or failed light attempt, and say so once.

An explicit user model or effort choice always wins. Hosts that cannot pause for confirmation should present the suggestion and treat the user's next instruction as the confirmation or override; they should not silently dispatch a surprising choice.

## Install in your agent

The canonical skill is [`skills/auto-model-router/SKILL.md`](skills/auto-model-router/SKILL.md). The root [`SKILL.md`](SKILL.md) contains the same body for easy discovery.

### Cursor

Copy the canonical skill into a project or user skills directory:

```bash
mkdir -p .cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md
```

You can also link or reference it from a Cursor rule (for example, a rule in `.cursor/rules/`) and tell the rule to follow `skills/auto-model-router/SKILL.md`. See [`integrations/CURSOR.md`](integrations/CURSOR.md) for the suggest → confirm wiring and model-picker mapping.

### Claude (Claude Code / projects)

Copy the skill into project-local Claude instructions:

```bash
mkdir -p .claude/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md
```

Alternatively, include the skill's contents or a repository reference from `CLAUDE.md` / project instructions. See [`integrations/CLAUDE.md`](integrations/CLAUDE.md).

### Codex

Add the skill's contents to `AGENTS.md` or your project instructions, or copy it into a skills folder if your Codex setup supports skills:

```bash
cat skills/auto-model-router/SKILL.md >> AGENTS.md
```

Prefer a clearly marked section or a referenced copy when `AGENTS.md` already contains project policy. See [`integrations/CODEX.md`](integrations/CODEX.md).

### Any multi-model agent

Paste [`SKILL.md`](SKILL.md) into system/custom instructions, project instructions, or the agent's skill directory. Then map the four neutral tiers to the models or effort controls available in that host. The optional [`demo/classify.py`](demo/classify.py) provides dependency-free offline checks; it does not call a model or provider.

## Tier rubric

These are capability tiers, not vendor product names:

| Tier | Use when |
| --- | --- |
| **fast** | Clear, bounded, reversible work: rename, format, short factual answer, simple procedure, or short summary. |
| **standard** | Multi-file edits, known patterns, routine features, or moderate debugging with useful clues. |
| **reasoning** | Ambiguous requirements, unknown-root-cause debugging, architecture, tradeoffs, or security-sensitive work. |
| **max** | Research-level questions, large ambiguous redesigns, formal reasoning, or the hardest judgment calls. |

Prefer lighter for reversible experiments and drafts. Do not under-provision security-sensitive or irreversible work. A host may map multiple tiers to the same model while preserving the four-tier decision and the user's ability to override.

## Offline demo

The demo is intentionally dependency-free Python 3:

```bash
python3 demo/classify.py --examples
python3 demo/classify.py "Rename foo to bar in utils.py"
python3 demo/classify.py --suggest "Debug intermittent auth failures"
echo "Debug intermittent auth failures" | python3 demo/classify.py
```

`--suggest` prints a human-facing suggestion followed by JSON. The normal output is JSON with `tier`, `reason`, `signals`, and `confidence`.

## Honest scope

This is a readable heuristic rubric and a portable agent skill, **not production ML** and not a benchmark of any provider. Real deployments should calibrate mappings against their own models, latency, cost, quality, and safety data. The stable contract is the user-controlled flow: **context → classify → suggest → confirm/override → run → escalate**.

## Repository layout

```text
README.md
LICENSE
.gitignore
SKILL.md                              # compatibility copy of the canonical skill
skills/auto-model-router/SKILL.md     # canonical skill
integrations/CURSOR.md
integrations/CLAUDE.md
integrations/CODEX.md
demo/classify.py                       # offline heuristic checker
examples.md
```

## License

MIT. See [`LICENSE`](LICENSE).
