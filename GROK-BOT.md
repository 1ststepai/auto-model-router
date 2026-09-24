# Auto Model Router for Grok Bot

Create an account-level private skill named **Auto Model Router** from `skills/auto-model-router/SKILL.md`.

Preserve the canonical sequence: context, classify, suggest, gate, run, and escalate. Honor explicit model choices. Auto-continue only clear, reversible fast work; standard, reasoning, max, security-sensitive, expensive, or irreversible work must wait at the skill's confirmation boundary. The skill must not invent Grok model names, silently change the selected model, claim access to billing data, or represent a text instruction as a hard runtime enforcement hook.

After saving it in Grok Bot, test one reversible fast task and one high-risk task. Confirm the first produces the suggestion before proceeding and the second stops for authorization.
