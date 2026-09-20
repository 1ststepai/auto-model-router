# Install the Auto Model Router

This repository is an agent behavior skill. Install it as a **plugin** from this GitHub repo (preferred when your host supports marketplace install) or copy the skill with the apply script. When you want the policy on every request, add the optional host rule or instruction file described below.

Plugin or skill install loads the suggest → confirm policy. It does **not** change Cursor, Claude Code, or Codex billing APIs, and it does **not** guarantee savings.

## Install as a plugin

This repo is its own plugin package. The canonical skill stays at [`skills/auto-model-router/SKILL.md`](skills/auto-model-router/SKILL.md). Host manifests point at that path — there is no second skill body.

These steps install from **this GitHub repository** (or a local clone). They are not an official listing on Cursor’s public Marketplace or Anthropic’s official plugin catalogs.

A plugin install does **not** open the savings dashboard. Use the [apply script](#recommended-apply-script-dashboard-auto-starts) (or open `demo/dashboard.html`) when you want the local estimator UI.

### Cursor

**Teams / Enterprise (preferred):** import this GitHub repo as a team marketplace, then install the plugin from Customize.

1. Open **Dashboard → Plugins & MCPs → Add Marketplace → Import from Repo**.
2. Paste `https://github.com/1ststepai/auto-model-router`.
3. Review and add the `auto-model-router` plugin, then save marketplace access.
4. In Cursor, open **Customize → Plugins** and install **Auto Model Router** (user or project scope).

The repo includes `.cursor-plugin/plugin.json` (Cursor plugin) plus a root `plugin.json` (Agent Plugins). `.cursor-plugin/marketplace.json` is what Teams import.

**If your Cursor build can add a plugin or skill from GitHub** (Customize → Plugins, or Skills from GitHub), use `1ststepai/auto-model-router`. That path depends on your Cursor version; it is not the public Marketplace catalog.

**Local plugin fallback:** copy this clone into `~/.cursor/plugins/local/auto-model-router` (a real directory — Cursor skips a symlink that points outside that folder), then reload the window and check Customize.

**Skill-only fallback:**

```bash
./scripts/apply.sh --no-open
# or:
mkdir -p ~/.cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md ~/.cursor/skills/auto-model-router/SKILL.md
```

### Claude Code

In a Claude Code session:

```text
/plugin marketplace add 1ststepai/auto-model-router
/plugin install auto-model-router@auto-model-router
/reload-plugins
```

Equivalent CLI:

```bash
claude plugin marketplace add 1ststepai/auto-model-router
claude plugin install auto-model-router@auto-model-router
```

The marketplace name in those commands is the `name` in `.claude-plugin/marketplace.json` (`auto-model-router`), not the GitHub owner. From a local clone you can use `/plugin marketplace add .` instead of the GitHub shorthand.

**Skill-only fallback:** `./scripts/apply.sh --no-open`, or copy `skills/auto-model-router/SKILL.md` into `.claude/skills/auto-model-router/` (project) or `~/.claude/skills/auto-model-router/` (user).

### Codex

```bash
codex plugin marketplace add 1ststepai/auto-model-router
codex plugin add auto-model-router@auto-model-router
```

That registers `.agents/plugins/marketplace.json` from this repo, then installs the plugin. The package is a portable Agent Plugins root `plugin.json` (skills discovered under `skills/`) with a `.codex-plugin/plugin.json` compatibility overlay that sets `"skills": "./skills/"`.

If you already have a clone, you can add it as a local marketplace:

```bash
codex plugin marketplace add /path/to/auto-model-router
codex plugin add auto-model-router@auto-model-router
```

**Skill-only fallback:** `./scripts/apply.sh --no-open`, or copy the skill into `.agents/skills/auto-model-router/` and/or add a marked section to `AGENTS.md`.

## Recommended: apply script (dashboard auto-starts)

**"Apply" means run the script below** — not only dropping `SKILL.md` into a skills folder. Cursor/Claude loading a skill cannot open a GUI; the apply scripts copy the skill, install the demo under `~/.auto-model-router/demo` (Windows: `%USERPROFILE%\.auto-model-router\demo`), create an empty `logs/usage.jsonl`, and by default **open `dashboard.html` in your default browser**.

From a clone of this repository:

```bash
# macOS/Linux — default: open dashboard
./scripts/apply.sh
# Skip opening the browser (also saves the preference)
./scripts/apply.sh --no-open
# Force open and re-enable auto-open preference
./scripts/apply.sh --open

# Windows PowerShell
.\scripts\apply.ps1
.\scripts\apply.ps1 -NoOpen
.\scripts\apply.ps1 -Open
```

**Preferences** live in `~/.auto-model-router/config.json` (Windows: `%USERPROFILE%\.auto-model-router\config.json`):

```json
{ "openDashboardOnApply": true, "weeklyReview": false }
```

- `--no-open` / `-NoOpen` sets `openDashboardOnApply` to `false` (persisted). `--open` / `-Open` sets it back to `true`. Default when missing is open (`true`).
- Weekly review is **off by default** (opt-in). See [Optional weekly review](#optional-weekly-review) below.

After it opens, click **Load sample log** for illustrative estimates (not live Cursor/Claude/Codex billing). Manual `cp` of `SKILL.md` alone does **not** auto-start the dashboard.

## Optional weekly review

Weekly reviews summarize your **local** `~/.auto-model-router/logs/usage.jsonl` (tiers confirmed/overridden, counts, illustrative relative-unit estimates). They do **not** read Cursor, Claude Code, Codex, or any vendor billing/token API.

```bash
# Enable / disable (persists weeklyReview in config.json)
./scripts/apply.sh --enable-weekly-review
./scripts/apply.sh --disable-weekly-review
# Windows PowerShell
.\scripts\apply.ps1 -EnableWeeklyReview
.\scripts\apply.ps1 -DisableWeeklyReview

# Run a review now (works even when disabled if you pass --force)
python3 ~/.auto-model-router/weekly_review.py --force
# or from a clone:
python3 scripts/weekly_review.py --force

# Optional: also open the savings dashboard after the summary
python3 scripts/weekly_review.py --force --open
```

To run truly weekly without thinking about it, use your OS scheduler — **nothing is installed silently**. You can either:

1. Add a cron / Task Scheduler entry yourself (recommended if you want full control), for example Mondays 09:00:
   - macOS/Linux cron: `0 9 * * 1 python3 ~/.auto-model-router/weekly_review.py --force`
   - Windows Task Scheduler: weekly trigger running `python %USERPROFILE%\.auto-model-router\weekly_review.py --force`
2. Or pass an **explicit** opt-in flag on apply (also sets `weeklyReview=true`):

```bash
./scripts/apply.sh --install-schedule     # user crontab Mondays 09:00
./scripts/apply.sh --uninstall-schedule   # remove that crontab entry
# Windows
.\scripts\apply.ps1 -InstallSchedule    # task AutoModelRouterWeeklyReview
.\scripts\apply.ps1 -UninstallSchedule
```

## What this supports

- **Cursor Agent**, using project or user skills and optional Cursor rules.
- **Claude Code**, using project or personal skills and `CLAUDE.md` instructions.
- **Codex**, using `AGENTS.md` and, where enabled, a skills directory.
- **Any coding agent** that accepts custom instructions, project instructions, or Agent Skills. Copy or paste the policy, then map `fast`, `standard`, `reasoning`, and `max` to that host's models or effort controls.

## What this does not do

This does **not** replace or configure Cursor's built-in **Auto** model picker by itself. It is agent behavior instructions: the agent assesses the task, shows a tier suggestion, waits for confirmation or an override, and then uses the host's model picker or effort setting. A host's native Auto mode can still make its own choice unless you change that host setting.

If you are running out of usage or burning tokens, this targets **model overkill**: suggest a lighter tier when it is sufficient, then confirm before substantial work. It can help slow usage burn only when that confirmed tier is mapped to a cheaper/faster model or lower effort and that option actually runs. Tools such as **lean.ctx** and **ponytail** are complementary peers—not competitors and not affiliated with this project—that reduce how much context you send; this skill does not shrink context or guarantee savings. Together they form a usage-discipline stack, not a promise of measured Cursor/Claude/Codex quota reduction.

## Quick start (about 60 seconds)

**Preferred:** clone this repository and run `./scripts/apply.sh` (macOS/Linux) or `.\scripts\apply.ps1` (Windows) so skills install **and** the savings dashboard opens by default (use `--no-open` / `-NoOpen` to skip; preference saved under `.auto-model-router/config.json`). For project-only installs without the dashboard auto-start, download or clone, then run the commands below from the **root of your target project**. Replace `/path/to/auto-model-router` with the location of this clone. If the target project is this repository itself, the shorter relative source paths shown in the host sections also work. Project installs are the best choice for teams and cloud/background agents because the files can be committed:

```bash
# Cursor
mkdir -p .cursor/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md

# Claude Code
mkdir -p .claude/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md

# Codex (if your setup supports Agent Skills)
mkdir -p .agents/skills/auto-model-router
cp /path/to/auto-model-router/skills/auto-model-router/SKILL.md .agents/skills/auto-model-router/SKILL.md
```

For a user-wide install, follow the host-specific paths below. Then **start a new chat/session**, ask for a moderate task without naming a model, and look for a line like:

```text
Auto suggests standard — this multi-file routine change fits the standard tier. Confirm to run, or override: fast, standard, reasoning, or max.
```

Confirm (or override) before allowing the agent to edit. If the host cannot pause, the suggestion must still appear and your next instruction acts as confirmation.

## Cursor

### Project install (recommended for teams and cloud agents)

Run from the root of your target project. If this repository is elsewhere, use its path as the source:

**macOS/Linux**

```bash
mkdir -p .cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .cursor/skills/auto-model-router/SKILL.md
```

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force .cursor\skills\auto-model-router | Out-Null
Copy-Item C:\path\to\auto-model-router\skills\auto-model-router\SKILL.md .cursor\skills\auto-model-router\SKILL.md
```

Commit `.cursor/skills/auto-model-router/SKILL.md` if other people or a remote agent should use it.

### User-wide install

Copy `SKILL.md` to the following local-machine directory (the skill folder must contain `SKILL.md`):

| OS | Path |
| --- | --- |
| Windows | `%USERPROFILE%\.cursor\skills\auto-model-router\SKILL.md` |
| macOS/Linux | `~/.cursor/skills/auto-model-router/SKILL.md` |

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.cursor\skills\auto-model-router" | Out-Null
Copy-Item skills\auto-model-router\SKILL.md "$env:USERPROFILE\.cursor\skills\auto-model-router\SKILL.md"
```

**macOS/Linux:**

```bash
mkdir -p ~/.cursor/skills/auto-model-router
cp skills/auto-model-router/SKILL.md ~/.cursor/skills/auto-model-router/SKILL.md
```

Cursor also recognizes `.agents/skills/` and compatibility skill directories, but `.cursor/skills/` is the clearest choice for this install.

### Optional always-apply rule

If the skill is present in the project, create `.cursor/rules/auto-model-router.mdc` and commit it with the skill:

```md
---
description: Ask for a tier confirmation before substantial model-dependent work
alwaysApply: true
---

Before substantial work or an open model/effort choice, read and follow
`.cursor/skills/auto-model-router/SKILL.md`. Show the required Auto suggests
line, wait for confirmation or an override, then use Cursor's model picker.
Honor any explicit model, provider, effort, or tier choice.
```

The rule makes the behavior more discoverable; it does not take control of Cursor's native Auto picker. If you use only a user-wide skill, install an equivalent user-wide rule if your Cursor version supports user rules, or rely on the skill's description and invoke it in the chat.

### Verify in Cursor

1. Open a **new Agent chat** in the project (or restart Cursor after a user-wide install).
2. Ask for a mid-weight task, such as: “Add a small validation helper and its tests to this project.” Do not name a model.
3. Before editing, Agent should show `Auto suggests <tier> — <reason>. Confirm to run, or override...`.
4. Reply `confirm` or choose another tier. The agent should then use the mapped Cursor picker/effort setting.

## Claude Code

### Project install

From the root of your target project:

**macOS/Linux or WSL**

```bash
mkdir -p .claude/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .claude/skills/auto-model-router/SKILL.md
```

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force .claude\skills\auto-model-router | Out-Null
Copy-Item C:\path\to\auto-model-router\skills\auto-model-router\SKILL.md .claude\skills\auto-model-router\SKILL.md
```

Commit `.claude/skills/auto-model-router/SKILL.md` for a team or cloud session.

### User-wide install

| OS | Path |
| --- | --- |
| Windows (native) | `%USERPROFILE%\.claude\skills\auto-model-router\SKILL.md` |
| macOS/Linux/WSL | `~/.claude/skills/auto-model-router/SKILL.md` |

`~` is normally `%USERPROFILE%` on native Windows. If `CLAUDE_CONFIG_DIR` is set, Claude uses that directory as the base instead.

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\auto-model-router" | Out-Null
Copy-Item skills\auto-model-router\SKILL.md "$env:USERPROFILE\.claude\skills\auto-model-router\SKILL.md"
```

**macOS/Linux/WSL:**

```bash
mkdir -p ~/.claude/skills/auto-model-router
cp skills/auto-model-router/SKILL.md ~/.claude/skills/auto-model-router/SKILL.md
```

### `CLAUDE.md` include option

Instead of relying on skill discovery, add this to the project `CLAUDE.md` (or your user-level `CLAUDE.md`) when the referenced file is available from that instruction file:

```md
@.claude/skills/auto-model-router/SKILL.md
```

Keep the include and skill in the repository for cloud use. Do not paste a second, diverging copy unless you intend to maintain it.

### Verify in Claude Code

Start a new Claude Code session after a new top-level skills directory is created. Ask the same kind of mid-weight task without specifying a model or effort. Claude should present the `Auto suggests ... Confirm to run, or override...` line before changing files; reply `confirm` or override explicitly.

## Codex

Codex reads `AGENTS.md` before work. Add a clearly marked section to the project `AGENTS.md` and paste the contents of [`SKILL.md`](SKILL.md), or tell Codex to follow the committed skill file:

```md
## Auto model routing

Before substantial work or an open model/effort choice, read and follow
`.agents/skills/auto-model-router/SKILL.md`. Show the Auto suggests line and
wait for confirmation or an explicit override before editing.
```

If Agent Skills are enabled, the current repository/user locations are:

| Scope | macOS/Linux | Windows |
| --- | --- | --- |
| Project | `.agents/skills/auto-model-router/SKILL.md` | `.agents\skills\auto-model-router\SKILL.md` |
| User-wide | `~/.agents/skills/auto-model-router/SKILL.md` | `%USERPROFILE%\.agents\skills\auto-model-router\SKILL.md` |

**Project install (macOS/Linux):**

```bash
mkdir -p .agents/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .agents/skills/auto-model-router/SKILL.md
```

**Project install (Windows PowerShell):**

```powershell
New-Item -ItemType Directory -Force .agents\skills\auto-model-router | Out-Null
Copy-Item skills\auto-model-router\SKILL.md .agents\skills\auto-model-router\SKILL.md
```

Some older or configured Codex installations also scan `$CODEX_HOME/skills` (normally `~/.codex/skills`, or `%USERPROFILE%\.codex\skills` on Windows). Use that compatibility location only when your installation documents it; `.agents/skills` is the portable project location.

### Verify in Codex

Start a new Codex run/session so `AGENTS.md` and the skill are read. Ask for a moderate task without selecting a model or reasoning effort. Before making changes, Codex should print the suggestion line and wait for `confirm` or an explicit override. If a TUI session loads instructions only at startup, fully restart it after changing `AGENTS.md`.

## Savings estimator (optional)

The repository includes an honest, offline MVP for estimating relative costs from routing decisions. It does not read live Cursor, Claude Code, or Codex billing/token data, scrape a GUI, or access credentials. It uses example relative rates only: `fast=1x`, `standard=3x`, `reasoning=8x`, `max=20x`; any percentage is an estimate from your supplied local log, not a guarantee or measured vendor saving.

```bash
python3 demo/savings_estimator.py demo/sample_usage_log.json
```

You can pass a JSON list of task strings (the demo classifies them) or a decision log with `tier`, `confirmed`, `overridden`, and `timestamp`. For a no-build visual view, run `./scripts/apply.sh` / `.\scripts\apply.ps1` (opens the installed copy under `~/.auto-model-router/demo/dashboard.html`), or open [`demo/dashboard.html`](demo/dashboard.html) from the repo, then click **Load sample log**, or paste your own JSON. After confirmed runs, agents may append non-sensitive decisions to `.auto-model-router/usage.jsonl`; the schema is documented in [`SKILL.md`](SKILL.md). Never log prompts, secrets, code, or customer data by default.

## Any other agent

Put the contents of [`SKILL.md`](SKILL.md) in the agent's custom/system/project instructions or its supported skill directory. If it supports a repository instruction file, commit the policy there. Map the neutral tiers to the available model or effort controls, and preserve this contract:

```text
context → classify → suggest → confirm/override → run → escalate if needed
```

If the host has no model control, still display the suggestion and ask for confirmation; do not claim that the host switched models.

## Cloud and background agents

You **must not** rely on a user-home install for a cloud VM, background agent, remote worker, or fresh checkout. Those machines generally do not have your local `~/.cursor`, `%USERPROFILE%\.cursor`, `~/.claude`, or Codex home directory. Put the **skill and any rule/instruction file in the repository**, for example:

```text
.cursor/skills/auto-model-router/SKILL.md
.cursor/rules/auto-model-router.mdc       # if using Cursor
.claude/skills/auto-model-router/SKILL.md # if using Claude Code
.agents/skills/auto-model-router/SKILL.md # if using Codex skills
AGENTS.md or CLAUDE.md                    # if using project instructions
```

Commit the files and confirm that the cloud agent checks out the same branch/commit. A host-specific sync feature may offer an additional way to share personal skills, but the repository copy is the dependable option for reproducible cloud runs.

## Verify the complete flow

Use a new chat/session and a mid-weight request with no explicit model choice. You should see a suggestion and reason **before coding**, followed by a confirmation request. Confirm it, or override with `fast`, `standard`, `reasoning`, `max`, or a host model/effort. The agent should then work with the mapped setting and mention a one-time escalation if the chosen tier proves insufficient.

## Troubleshooting

### An old chat does not use the skill

Start a new chat or fully restart the agent. Many hosts snapshot instructions at session start; Claude Code may need a restart when a new top-level skills directory is first created, and Codex reads `AGENTS.md` at startup.

### The skill is not loaded

Check the exact path, spelling, and required filename `SKILL.md`; keep it inside a folder named `auto-model-router`. Open the host's discovered-skills/instructions view if it has one. For project installs, launch the agent from the repository or a child directory and commit the file. For Codex, prefer `.agents/skills`; for Cursor/Claude, use the host paths above.

### The agent works but stays silent

Check that you installed the optional Cursor rule or added the relevant `AGENTS.md`/`CLAUDE.md` instruction. A skill may be discovered but invoked only when relevant. Ask explicitly: “Apply the auto-model-router policy and suggest a tier before editing.”

### Cursor's Auto still chooses silently

That is separate from this skill. The skill cannot replace Cursor's built-in Auto picker or force a provider/model change. Verify that the agent itself printed the suggestion and waited for your confirmation; then choose the mapped model/effort in Cursor if needed.

### Cloud cannot find it

Confirm the skill and rule are committed under the repository, not only under your local home directory. Check the cloud job's checked-out commit and its host-specific project path.
