# Gemini integration

For the complete cross-host guide, see [`../INSTALL.md`](../INSTALL.md).

Gemini is a first-class host for this skill: **Gemini CLI** (skill directory + optional hooks), **Google AI Studio**, **Antigravity**, and other Gemini-backed coding agents. There is **no official Google plugin catalog listing** for this repo. Do not treat `gemini skills install` as a marketplace badge. This repo does not ship a `.gemini-plugin` marketplace.

## Install (Gemini CLI)

**Preferred — project skill (teams and cloud agents):**

```bash
mkdir -p .gemini/skills/auto-model-router
cp skills/auto-model-router/SKILL.md .gemini/skills/auto-model-router/SKILL.md
```

Gemini CLI also discovers `.agents/skills/` as an alias. User-wide:

| OS | Path |
| --- | --- |
| macOS/Linux | `~/.gemini/skills/auto-model-router/SKILL.md` |
| Windows | `%USERPROFILE%\.gemini\skills\auto-model-router\SKILL.md` |

`./scripts/apply.sh` / `.\scripts\apply.ps1` copy the skill into `~/.gemini/skills/auto-model-router/` along with the other hosts.

**Gemini CLI skill install** (user scope by default; not an official Google catalog):

```bash
gemini skills install https://github.com/1ststepai/auto-model-router.git --path skills/auto-model-router
# project only:
gemini skills install https://github.com/1ststepai/auto-model-router.git --path skills/auto-model-router --scope workspace
```

If `gemini skills` is missing or the `--path` flag differs on your CLI version, use the `cp` path above. Then `/skills list` or `gemini skills list --all`, and start a **new** session. Workspace skills load only when the folder is trusted (`/trust`).

### `GEMINI.md` (always-on)

To keep the policy in context every turn, add a marked include from project `GEMINI.md`:

```md
## Auto model routing

Before substantial work or an open model/effort choice, read and follow
`.gemini/skills/auto-model-router/SKILL.md`. Auto-continue only clear reversible
fast work. Wait for confirm or override on standard / reasoning / max and
high-risk work.
```

### Google AI Studio, Antigravity, and other Gemini UIs

AI Studio, Antigravity, and similar UIs do not load a Google plugin marketplace from this repo. If the host reads `.gemini/skills/` or `GEMINI.md`, use the copy/include above. Otherwise paste the skill (or the include) into custom / system instructions, then pick the mapped model in the UI **after** the gate. That is still suggest → gate → run. It is not a silent model switch, not a billing integration, and not an official Google catalog listing.

## Capability map (families, not frozen IDs)

Copy [`gemini-tier-map.example.json`](gemini-tier-map.example.json) to `.auto-model-router/gemini-tier-map.json` or `~/.auto-model-router/gemini-tier-map.json` and fill in **your** picker labels. Google renames models; the skill must not hard-code IDs.

| AMR tier | Gemini family (example) | Typical use |
| --- | --- | --- |
| **fast** | Flash / Flash-Lite | Clear, reversible, low-judgment work |
| **standard** | Pro (default, no extra thinking) | Multi-file routine features — **still confirms** |
| **reasoning** | Pro with thinking / higher reasoning | Ambiguous, architecture, security (hard-gate when high-risk) |
| **max** | Deep / thinking-max / strongest available | Research-level or large ambiguous redesigns |

Hosts rename locally. A project may map two AMR tiers onto the same Gemini model and still show the four-tier suggestion.

Preview:

```bash
python3 demo/classify.py --suggest --map integrations/gemini-tier-map.example.json \
  --host Gemini --current-tier max "Rename the variable foo to bar in utils.py"
```

## Wire suggest → gate

1. Classify as `fast`, `standard`, `reasoning`, or `max`. Same confirm gate as every other host.
2. Emit `Auto continues on fast — …` or `Auto suggests <tier> — … Confirm to run…`. Name the mapped Gemini family from the local map; do not invent an ID.
3. Auto-continue only clear reversible `fast`. Spendy / high-risk wait.
4. Optional hard block: merge [`../hooks/gemini.settings.snippet.json`](../hooks/gemini.settings.snippet.json) into `.gemini/settings.json` (`BeforeAgent` + `BeforeTool`). Gemini CLI exit 2 / `decision: deny` blocks the tool. Trust project hooks. A skill alone is not a runtime block.
5. After a failed light attempt, stop for confirm and escalate.

Gemini CLI hosted tools and the AI Studio model picker can still spend without a local `BeforeTool` hook. This repo cannot hard-block that, and it does not read Google usage or billing APIs.

## Verify

Start a new Gemini CLI session after installing. A clear rename should print `Auto continues on fast`. A CRUD or auth task should wait. Reply `confirm` or override. For cloud/background runs, commit `.gemini/skills/auto-model-router/SKILL.md` (and `GEMINI.md` if you use it).
