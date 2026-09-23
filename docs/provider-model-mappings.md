# Provider model mappings

Checked **2026-09-23** against the providers' official documentation.

AMR must recommend a concrete model for Codex, Claude, and Gemini. The checked-in defaults provide a useful starting point; the current host inventory, a project mapping, or an explicit user choice takes precedence. If a named model is unavailable, report that fact and use the nearest available model in the same provider and tier. Never silently switch providers.

| Tier | Codex | Claude | Gemini |
| --- | --- | --- | --- |
| fast | `gpt-6-luna`, `none` | `claude-haiku-4-5-20251001`, host default | `gemini-3.5-flash-lite`, `minimal` |
| standard | `gpt-6-sol`, `medium` | `claude-sonnet-5`, `low` | `gemini-3.8-flash`, `medium` |
| reasoning | `gpt-6-astra`, `high` | `claude-opus-5`, `high` | `gemini-3.1-pro-preview`, `high` |
| max | `gpt-6-astra`, `max` | `claude-opus-5`, `max` | `gemini-3.1-pro-preview`, `high`; research-only alternative `deep-research-max-preview-04-2026` |

The Gemini general-purpose maximum uses the same Pro model and supported `high` thinking level as reasoning because Gemini does not expose a higher general-purpose thinking level for that model. The separate Deep Research Max endpoint is appropriate only when the job is research rather than coding or routine agent work.

## Official evidence

- OpenAI model catalog and supported reasoning efforts: https://developers.openai.com/api/docs/models
- Anthropic active model lifecycle: https://docs.anthropic.com/en/docs/about-claude/model-deprecations
- Anthropic adaptive thinking and effort guidance: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables
- Gemini model catalog: https://ai.google.dev/gemini-api/docs/models
- Gemini supported thinking levels: https://ai.google.dev/gemini-api/docs/thinking

## Maintenance

1. Recheck all official catalogs when a provider rejects an ID, announces a retirement, or the checked date is older than 90 days.
2. Update `integrations/provider-tier-defaults.json`, this document, the canonical skill, and its root mirror together.
3. Validate JSON and run the repository test suite.
4. Keep preview status visible. Do not present a preview model as stable.
