<p align="center">
  <img src="assets/logo.png" alt="1stStep.ai Auto Model Router" width="220">
</p>

# Portable Auto router for any multi-model coding agent

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md) [![Python demo](https://img.shields.io/badge/demo-Python%203-3776AB.svg?logo=python&logoColor=white)](demo/classify.py)

**A transparent, user-confirmed policy that routes each coding-agent task to the lightest sufficient model or effort tier.** It is for developers and teams using **Cursor, Claude Code, Codex, or any agent with custom instructions or skills**—without requiring vendor-specific model names or APIs.

An open-source, provider-agnostic skill for routing coding-agent work to the lightest model or effort tier that can do it well.

**Flow:** context → classify (`fast` / `standard` / `reasoning` / `max`) → suggest → user confirm/override → run.

The repository contains a portable skill, small offline heuristic demo, integration notes, and examples. Copy the skill into each project or add it to your user-level agent instructions so all your projects can use the same routing policy.

## Install

**Start with the complete [installation guide](INSTALL.md).** It covers plugin installs, project and user-wide skill copies, Windows and macOS/Linux paths, Cursor, Claude Code, Codex, generic agents, cloud/background agents, and verification.

The canonical skill is [`skills/auto-model-router/SKILL.md`](skills/auto-model-router/SKILL.md). The root [`SKILL.md`](SKILL.md) contains the same body for easy discovery. Plugin manifests for Cursor, Claude Code, and Codex all point at that skill — they do not ship a second policy.

Installing the plugin loads the suggest → confirm skill. It does **not** change vendor billing APIs or guarantee savings.

### Install as a plugin

Use each host’s native marketplace commands against this GitHub repo. These are not official Cursor Marketplace or Anthropic catalog listings.

```text
# Claude Code (in a session)
/plugin marketplace add 1ststepai/auto-model-router
/plugin install auto-model-router@auto-model-router
/reload-plugins
```

```bash
# Codex
codex plugin marketplace add 1ststepai/auto-model-router
codex plugin add auto-model-router@auto-model-router
```

**Cursor (Teams / Enterprise):** Dashboard → Plugins & MCPs → Import from Repo → `https://github.com/1ststepai/auto-model-router`, then Customize → Plugins → install Auto Model Router. Individuals can copy the clone into `~/.cursor/plugins/local/auto-model-router` or use the apply script / skill copy below.

Plugin install does not open the savings dashboard. Use the apply script for that.

### Apply (skill copy + dashboard auto-starts)

```bash
# macOS/Linux — default: open dashboard
./scripts/apply.sh
./scripts/apply.sh --no-open   # install only; persist preference
./scripts/apply.sh --open      # force open; persist preference

# Windows PowerShell
.\scripts\apply.ps1
.\scripts\apply.ps1 -NoOpen
.\scripts\apply.ps1 -Open
```

This copies the skill into user skills dirs (Cursor, Claude, Codex), installs the demo under `~/.auto-model-router/demo`, and by default opens the savings dashboard. Pass `--no-open` / `-NoOpen` to skip the browser; `--open` / `-Open` forces open. Choices are saved in `~/.auto-model-router/config.json` (Windows: `%USERPROFILE%\.auto-model-router\config.json`). Defaults include `openDashboardOnApply`, `weeklyReview`, `auditOptIn`, `hosts`, `usageLogPath`, and `boundaryGatedConfirms`. See [`integrations/config.example.json`](integrations/config.example.json).

**Savings Desk** (opt-in local audit, then automation — not vendor billing):

```bash
./scripts/apply.sh --enable-audit --no-open
python3 scripts/detect_active.py          # current host/tier from local context
python3 scripts/audit_usage.py --force    # audits that pick first, then asks optimize?
python3 scripts/apply_recommendations.py --yes --enable-weekly-review  # only after yes
# Dashboard: ~/.auto-model-router/demo/dashboard.html  or  demo/dashboard.html
```

Consent is required before agents append `usage.jsonl`. Collected: tier, host, confirmed/overridden, task_kind. Never: prompts, code, secrets, vendor credentials. Apply writes local `cursor-tier-map.json` plus Claude/Codex stubs and sets the boundary-gated confirm flag. See [`docs/SAVINGS_DESK.md`](docs/SAVINGS_DESK.md). After a successful audit (and after you say yes to optimize), AMR may optionally ask if you want to join **CodeFriends** — never required; set `codefriendsUrl` in config if you have an invite, otherwise it will not invent a domain.

**Optional weekly review** (local usage log only — not vendor billing):

```bash
./scripts/apply.sh --enable-weekly-review
python3 ~/.auto-model-router/weekly_review.py --force
# Explicit opt-in schedule only — never installed silently:
./scripts/apply.sh --install-schedule   # uninstall: --uninstall-schedule
```

**Dropping `SKILL.md` alone does not auto-start the dashboard** — that requires the apply script (or opening `demo/dashboard.html` yourself).

### Short CLI snippets

Run from the root of your target project; replace `/path/to/auto-model-router` with the clone location:

```bash
# Cursor
mkdir -p .cursor/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md

# Claude Code
mkdir -p .claude/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md

# Codex Agent Skills, when supported
mkdir -p .agents/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .agents/skills/auto-model-router/SKILL.md
```

For Codex setups using `AGENTS.md`, add a marked section that points to or contains the policy. For a user-wide install or Windows PowerShell commands, use [INSTALL.md](INSTALL.md).

### Quick demo

The dependency-free demo is a transparent rubric check, not ML and not a provider call:

```bash
python3 demo/classify.py --suggest "Wire up a CRUD endpoint using the existing handler pattern"
```

```text
Auto suggests **standard** — Multi-file edits, known patterns, or moderate debugging with decent clues; mid tier sufficient. Confirm to run, or override (fast | standard | reasoning | max).
--- JSON ---
{"tier": "standard", "reason": "Multi-file edits, known patterns, or moderate debugging with decent clues; mid tier sufficient.", "signals": ["known patterns"], "confidence": 0.7}
```

## Savings estimator

If you are running out of Cursor, Claude Code, or Codex usage, this project addresses the **model-overkill** part of the burn: it suggests the lightest tier that can do the job and asks for confirmation before substantial work. It can help slow usage burn **only when** the confirmed lighter tier is mapped to a cheaper/faster model or lower effort and that choice is what actually runs. The included estimator uses illustrative relative rates (`fast=1x`, `standard=3x`, `reasoning=8x`, `max=20x`) to compare your local routed log with always-reasoning and always-max baselines:

```bash
python3 demo/savings_estimator.py demo/sample_usage_log.json
# Or run ./scripts/apply.sh (opens ~/.auto-model-router/demo/dashboard.html), then Load sample log.
# Optional: open demo/dashboard.html from the repo and load the sample log or paste your own JSON.
```

This is not live billing or token accounting: coding-agent GUIs do not expose a reliable third-party billing API to this skill, so it does not scrape dashboards or access credentials. Percentages are estimates from the supplied local log, not promises or measured vendor savings. After confirmed runs **and only if `auditOptIn` is true**, an agent may append local, non-sensitive decisions to `.auto-model-router/usage.jsonl`; see [`SKILL.md`](SKILL.md) and [`docs/SAVINGS_DESK.md`](docs/SAVINGS_DESK.md) for the schema. Tools such as **lean.ctx** and **ponytail** are complementary peers: they reduce how much context you send, while this router reduces which model tier you spend on. Together they form a usage-discipline stack that may help slow burn when their respective choices actually reduce cost; there is no affiliation claim. See [`docs/STACK.md`](docs/STACK.md).

## Supported hosts

- [Cursor Agent](integrations/CURSOR.md) (project/user skills plus an optional always-apply rule)
- [Claude Code](integrations/CLAUDE.md) (project/personal skills or `CLAUDE.md`)
- [Codex](integrations/CODEX.md) (`AGENTS.md` and supported Agent Skills)
- Any agent with custom instructions or a skills directory

Cloud/background agents should use the committed project copy, not only a local user-home skill.

## How you'll know it works

Start a **new** chat/session and ask for a mid-weight task without naming a model. Before coding, you should see the suggest → confirm step:

```text
You: Wire up a CRUD endpoint using the existing handler pattern.
Agent: Auto suggests standard — this matches a known multi-file pattern. Confirm to run,
       or override: fast, standard, reasoning, or max.
You: confirm
Agent: [runs with your configured standard model/effort]
```

Then verify the agent uses the mapped model/effort. Cursor's built-in Auto picker remains a separate feature.

## Silent Auto vs this skill

| | Silent Auto / native picker | Auto Model Router |
| --- | --- | --- |
| Decision | Host chooses internally | Agent explains a capability tier first |
| User control | Depends on the host UI | Confirm or override before substantial work |
| Model names | Host-specific | Neutral tiers mapped locally to available models/effort |
| Cloud use | Host-dependent | Commit the skill and rule/instructions in the project |
| Scope | Native picker behavior | Portable agent instructions; does not replace native Auto |

## Why use it?

When people run out of usage or burn through tokens, over-provisioning is one avoidable source of waste: slow, expensive models get used for trivial edits while genuinely ambiguous work can still be under-provisioned. Auto model routing reduces that choice overhead **without silently changing what runs**:

Tools such as **lean.ctx** and **ponytail** address a complementary waste: they reduce how much context you send. This skill reduces which model tier you spend on, with a visible suggestion and confirmation before substantial work. It does not shrink context, and it can help slow usage burn only when a confirmed lighter tier actually maps to a cheaper/faster model or lower effort. Together, less context waste plus less model overkill may form a useful usage-discipline stack for Cursor/Claude/Codex. They are peer tools, not competitors, and this project is not affiliated with them; no savings are guaranteed.

1. Read the task context: scope, ambiguity, risk, reversibility, and judgment required.
2. Classify it into the lightest sufficient tier: `fast`, `standard`, `reasoning`, or `max`.
3. Suggest the tier and give a short reason.
4. Let the user confirm or override it.
5. Run with the chosen provider/model/effort mapping.
6. Escalate after a clearly insufficient or failed light attempt, and say so once.

An explicit user model or effort choice always wins. Hosts that cannot pause for confirmation should present the suggestion and treat the user's next instruction as the confirmation or override; they should not silently dispatch a surprising choice.

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
INSTALL.md
LICENSE
.gitignore
plugin.json                           # Agent Plugins 1.0 portable manifest
.cursor-plugin/plugin.json            # Cursor plugin
.cursor-plugin/marketplace.json       # Cursor team marketplace import
.claude-plugin/plugin.json            # Claude Code plugin
.claude-plugin/marketplace.json       # Claude Code marketplace
.codex-plugin/plugin.json             # Codex compatibility overlay
.agents/plugins/marketplace.json      # Codex repo marketplace
assets/logo.png                       # square plugin / marketplace tile
assets/logo-512.png                   # same 512×512 tile
assets/auto-model-router-logo.png     # original neon upload
SKILL.md                              # compatibility copy of the canonical skill
skills/auto-model-router/SKILL.md     # canonical skill (single source of truth)
scripts/apply.sh / apply.ps1           # apply skill + open dashboard (--no-open, weekly review, --enable-audit)
scripts/validate-plugins.py            # best-effort plugin manifest checks
scripts/weekly_review.py               # opt-in local usage-log weekly summary
scripts/amr_usage.py                   # shared local-log helpers (no vendor APIs)
scripts/audit_usage.py                 # Savings Desk audit (burns, confirm rate, relative units)
scripts/detect_active.py               # declare or infer current host/tier (no live picker)
scripts/apply_recommendations.py       # write local maps only after --yes
scripts/context_budget_checklist.md    # optional context-lean pairing checklist
integrations/CURSOR.md
integrations/CLAUDE.md
integrations/CODEX.md
integrations/*-tier-map.example.json   # local host map stubs (fill your picker labels)
demo/classify.py                       # offline heuristic checker
demo/savings_estimator.py              # relative usage estimator
demo/sample_usage_log.json             # fake demo routing log
demo/dashboard.html                    # Savings Desk no-build local dashboard
docs/SAVINGS_DESK.md                   # free skill vs paid desk (placeholders)
docs/STACK.md                          # AMR + context lean + Savings Desk
docs/boundary-gated-confirms.md        # confirm only at risk/ambiguity boundaries
examples.md
CONTRIBUTING.md
SECURITY.md
```

## License

MIT. See [`LICENSE`](LICENSE).
