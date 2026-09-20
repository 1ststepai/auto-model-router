# Auto model router — examples

These examples show the expected tier from the provider-agnostic prototype rubric in [`demo/classify.py`](demo/classify.py). In every host, Auto should suggest the tier and reason, wait for confirmation or an override, then map it to the configured model or effort.

| # | Real-world task | Expected tier | Why |
|---:|---|---|---|
| 1 | Rename the `customer_id` field to `account_id` in one config file | **fast** | Clear, bounded, reversible single-file edit. |
| 2 | Summarize the incident timeline in this issue into five bullets | **fast** | Short, bounded summarization. |
| 3 | Follow these steps to add a logging line to `main.py` | **fast** | The procedure is already specified. |
| 4 | Apply the same null-check pattern across a few files in the API client | **standard** | Multi-file change with a known pattern. |
| 5 | Wire up a CRUD endpoint using the existing handler pattern | **standard** | Routine feature work with a clear local shape. |
| 6 | Make a multi-file update to the SDK client and tests for the new pagination field | **standard** | Several coordinated edits following existing conventions. |
| 7 | Debug why checkout authentication fails intermittently in production | **reasoning** | Unknown root cause and operational risk require investigation. |
| 8 | Design the architecture for a multi-tenant billing system | **reasoning** | Architecture and tradeoff judgment are central. |
| 9 | Review this auth change for XSS, credential leaks, and unsafe redirects | **reasoning** | Security-sensitive review must not be under-provisioned. |
| 10 | Prove a novel consensus algorithm and redesign the distributed store | **max** | Formal reasoning plus a large, ambiguous redesign. |

## Suggest → confirm examples

```text
User: Apply the same null-check pattern across a few files in the API client.
Agent: Auto suggests standard — multi-file known-pattern work. Confirm to run,
       or override: fast, standard, reasoning, or max.
User: confirm
Agent: [maps standard to the host's configured model/effort and starts]
```

```text
User: Debug why checkout authentication fails intermittently in production.
Agent: Auto suggests reasoning — unknown-root-cause auth debugging needs investigation.
       Confirm to run, or override: fast, standard, reasoning, or max.
```

For mixed wording such as “draft a prototype redesign we can throw away,” reversible cues can bias toward a lighter tier. Security, irreversible actions, and a failed light attempt should still trigger escalation. These are expectations for a readable heuristic, not guarantees or a benchmark. Any usage benefit depends on the confirmed tier mapping and the option that actually runs.
