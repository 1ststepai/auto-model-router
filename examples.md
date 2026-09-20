# Auto model router — examples

Expected tiers from the provider-agnostic prototype rubric (`demo/classify.py`). In every host, Auto should suggest the tier and reason, wait for confirmation or an override, then map it to the configured model or effort.

| # | Task | Tier | Why |
|---|------|------|-----|
| 1 | Rename the variable `foo` to `bar` in `utils.py` | **fast** | Clear single-file rename; no judgment. |
| 2 | Summarize this 3-paragraph email in two bullets | **fast** | Short summarization of bounded text. |
| 3 | What is the capital of France? | **fast** | Short factual question. |
| 4 | Follow these steps to add a logging line to `main.py` | **fast** | Clear procedure given; execute as specified. |
| 5 | Apply the same null-check pattern across a few files | **standard** | Multi-file but known pattern; mid tier. |
| 6 | Wire up a CRUD endpoint using the existing handler pattern | **standard** | Known shape / existing pattern. |
| 7 | Debug why auth fails intermittently in production | **reasoning** | Unknown root cause; investigative judgment. |
| 8 | Design the architecture for a multi-tenant billing system | **reasoning** | Architecture / system design. |
| 9 | Investigate ambiguous requirements and propose an API shape | **reasoning** | Ambiguity + design judgment. |
| 10 | Review this auth change for XSS and credential leaks | **reasoning** | Security-sensitive review. |
| 11 | Prove a novel consensus algorithm and redesign the entire distributed store | **max** | Hard formal reasoning + large redesign. |
| 12 | Open-ended research: invent a new indexing approach for this corpus | **max** | Research-level / open-ended invention. |

## Suggest → confirm examples

| Task | Suggestion line |
|------|-----------------|
| Rename `foo` → `bar` | Auto suggests **fast** — clear single-file rename. Confirm to run, or override: fast, standard, reasoning, or max. |
| Intermittent auth debug | Auto suggests **reasoning** — unknown-root-cause auth debugging needs investigation. Confirm to run, or override: fast, standard, reasoning, or max. |
| Invent new indexing | Auto suggests **max** — open-ended research / hardest judgment. Confirm to run, or override: fast, standard, reasoning, or max. |

For mixed wording such as “draft a prototype redesign we can throw away,” reversible cues should bias toward the lighter tier. Security, irreversible actions, and a failed light attempt should still trigger escalation.
