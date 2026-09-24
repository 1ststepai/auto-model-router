# Runtime Portability Contract

`skills/auto-model-router/SKILL.md` is the canonical routing policy. Runtime adapters, hooks, and manifests may enforce or load it but must not create a divergent policy.

## Supported package surfaces

- Agent Plugins v1 and compatible future clients: `plugin.json`
- Codex: `.codex-plugin/plugin.json`
- Claude Code: `.claude-plugin/plugin.json`
- Cursor: `.cursor-plugin/plugin.json`, `.cursor/rules/`, and optional hooks
- Gemini CLI: `gemini-extension.json`, `GEMINI.md`, and optional hooks
- Grok Build: the portable skill and Claude-compatible plugin manifest, discovered through `~/.grok/plugins/auto-model-router`
- Grok Bot: `GROK-BOT.md` is the account-level private-skill handoff

## Adding another runtime

Reuse Agent Skills or Agent Plugins v1 when possible. Otherwise add the smallest adapter that maps the runtime's available models and effort controls into the canonical `fast`, `standard`, `reasoning`, and `max` tiers. Never invent a model name, silently change a user's explicit choice, bypass confirmation gates, or claim access to provider billing data. Validate fresh-session discovery before claiming activation.
