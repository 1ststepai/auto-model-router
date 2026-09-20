# Contributing

Thanks for helping make Auto Model Router clearer, safer, and more useful across coding-agent hosts.

## Before you start

1. Read [`README.md`](README.md), [`INSTALL.md`](INSTALL.md), and [`SKILL.md`](SKILL.md).
2. Keep the project provider-agnostic: use `fast`, `standard`, `reasoning`, and `max`, not a vendor's current model names.
3. Preserve the core UX: **context → classify → suggest → confirm/override → run → escalate**.
4. Be explicit that the rubric is a transparent heuristic, not ML or a security control.

## Improve the rubric

- Add or refine readable patterns in `demo/classify.py`.
- Add a representative input and expected tier to `EXAMPLES` in the same file.
- Update [`examples.md`](examples.md) when the user-facing rubric changes.
- Prefer a false-positive-resistant signal over a clever opaque rule. Keep explicit model/provider/effort choices as overrides.
- Run the example suite and inspect both the suggestion line and JSON output.
- Keep `demo/sample_usage_log.json`, `demo/savings_estimator.py`, and `demo/dashboard.html` honest about example rates and non-live data.

## Add a host adapter

Add concise host-specific guidance under `integrations/` and link it from [`INSTALL.md`](INSTALL.md) when needed. Document:

- project and user-wide install paths, including Windows when applicable;
- how the host maps neutral tiers to its available model/effort controls;
- how the host handles confirmation and a fresh-session reload;
- what cloud/background agents receive from the repository checkout.

Do not hard-code model names into the portable skill, and do not claim that an adapter controls a host's native Auto picker when it does not.

## Run checks locally

This repository intentionally has no third-party runtime dependencies:

```bash
python3 demo/classify.py --examples
python3 demo/classify.py --suggest "Debug intermittent checkout auth failures"
python3 -m compileall -q demo scripts
python3 demo/savings_estimator.py demo/sample_usage_log.json
python3 scripts/validate-plugins.py
git diff --check
```

Keep plugin manifests pointed at [`skills/auto-model-router/SKILL.md`](skills/auto-model-router/SKILL.md). Do not fork a second skill body under a host-specific plugin folder. If you change the skill, update the root [`SKILL.md`](SKILL.md) copy to match.

The first command should report every example passed. Also manually check Markdown links and code fences when changing documentation.

## Pull requests

Keep changes focused, explain the user benefit, and include the commands you ran. Documentation improvements should update the canonical install path or cross-host links rather than creating a second conflicting policy. Pull requests and constructive issue reports are welcome.
