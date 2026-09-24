# Adaptive routing without vendor lock-in

The router has three layers. They are deliberately separate so a project can
improve routing intelligence without weakening user control.

1. **Classifier:** the dependency-free heuristic is the default. Hosts may pass
   a local callable to `classify_task(..., classifier=...)` or
   `route(..., classifier=...)`. That callable can wrap ONNX, an embedding
   model, or another locally controlled predictor and returns `tier`,
   `confidence`, and `reason`.
2. **Safety envelope:** the built-in heuristic still owns hard gates. A custom
   classifier cannot lower a recognized high-risk task below `reasoning`, turn
   a boundary case into auto-continue, or bypass confirmation for a spendy tier.
   If the classifier fails or returns invalid output, routing falls back to the
   heuristic and reports `classification_source=heuristic_fallback`.
3. **Outcome evidence:** `record_outcome` stores non-sensitive task kind,
   success, latency, optional quality, tokens, and reported cost. It never stores
   the prompt or task text. `summarize_benchmarks` produces sufficiently sampled
   advisory groups; it never rewrites policy or switches models itself.

Every classification reports `classification_ms`. There is no universal
latency promise: ONNX and embedding speed depends on the chosen model, runtime,
and hardware. Benchmark the actual deployment before setting a target.

## Post-run cost summaries

`post_run_summary` shows reported cost when a host supplies `cost_usd`, or a
locally calculated cost when token counts and a complete local price table are
available. A comparison against another tier is labeled estimated and is only
shown when that baseline can also be priced. Otherwise the fields remain null.

The router does not scrape provider dashboards or claim access to vendor billing
APIs. A truthful summary may therefore say that actual cost or savings are
unavailable.

## Why Amazon Bedrock is an adapter, not the core architecture

Amazon Bedrock Intelligent Prompt Routing is a useful managed option for an AWS
deployment. AWS documents model-family routing, response-quality prediction,
and configurable routers. AWS also documents important boundaries: prompt
routing is English-only, works with exactly two models in the same family, and
does not adapt decisions from application-specific performance data. Those
constraints do not match a universal skill that must work across Claude Code,
Codex, Cursor, Gemini, Grok, and future hosts.

Use Bedrock behind a host adapter when the application is already on AWS. Keep
the portable classifier, safety envelope, outcome schema, and confirmation
contract as the provider-neutral core.

Primary references:

- [Amazon Bedrock intelligent prompt routing](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routing.html)
- [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [RouteLLM research paper](https://arxiv.org/abs/2406.18665)

