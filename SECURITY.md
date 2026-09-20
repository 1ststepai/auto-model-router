# Security

## Scope

Auto Model Router is a portable instruction skill and a small local heuristic demo. It does not make security decisions, enforce permissions, sandbox an agent, or guarantee safe model selection. Treat the tier suggestion as a workflow aid, not a security control.

The heuristic intentionally routes authentication, secrets, irreversible actions, and other security-sensitive work toward stronger reasoning, but users and host safeguards remain responsible for review and authorization.

## Secrets and sensitive data

- The skill contains no credentials, API keys, tokens, or required network calls.
- Do not commit secrets, private prompts, customer data, or proprietary logs to this repository or to issue reports.
- Review any copied skill, custom rule, `AGENTS.md`, or `CLAUDE.md` before sharing it; repository instructions are executable context for an agent.
- Keep provider credentials in the host's supported secret store, never in the skill or examples.

## Reporting

For a suspected vulnerability in this repository, avoid posting sensitive details publicly. Contact the repository maintainers privately through the GitHub organization or the contact method configured on the repository, and include reproduction steps without credentials. For ordinary rubric bugs or documentation issues, use the public issue templates.
