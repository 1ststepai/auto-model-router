# Auto model router — examples

These examples show the expected tier and confirm **gate** from the provider-agnostic prototype rubric in [`demo/classify.py`](demo/classify.py). Clear reversible `fast` work auto-continues. Spendy tiers (`standard`, `reasoning`, `max`) and high-risk work wait for confirmation or an override, then map to the configured model or effort.

| # | Real-world task | Expected tier | Gate | Why |
|---:|---|---|---|---|
| 1 | Rename the `customer_id` field to `account_id` in one config file | **fast** | auto_continue | Clear, bounded, reversible single-file edit. |
| 2 | Summarize the incident timeline in this issue into five bullets | **fast** | auto_continue | Short, bounded summarization. |
| 3 | Follow these steps to add a logging line to `main.py` | **fast** | auto_continue | The procedure is already specified. |
| 4 | Apply the same null-check pattern across a few files in the API client | **standard** | confirm | Multi-file change with a known pattern — spendy, so wait. |
| 5 | Wire up a CRUD endpoint using the existing handler pattern | **standard** | confirm | Routine feature work; spendy tier still confirms. |
| 6 | Rename the helper and apply the same null-check pattern across a few files | **standard** | confirm | Near-boundary mix of fast + standard families. |
| 7 | Debug why checkout authentication fails intermittently in production | **reasoning** | hard_gate | Unknown root cause plus auth/security risk. |
| 8 | Design the architecture for a multi-tenant billing system | **reasoning** | confirm | Architecture and tradeoff judgment are central. |
| 9 | Review this auth change for XSS, credential leaks, and unsafe redirects | **reasoning** | hard_gate | Security-sensitive review must not be under-provisioned. |
| 10 | Prove a novel consensus algorithm and redesign the distributed store | **max** | confirm | Formal reasoning plus a large, ambiguous redesign. |

## Suggest → gate examples

```text
User: Rename the variable foo to bar in utils.py
Agent: Auto continues on fast — clear bounded rename.
```

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
       Confirm required (high-risk / hard to undo), or override: fast, standard, reasoning, or max.
```

For mixed wording such as “draft a prototype redesign we can throw away,” reversible cues can bias toward a lighter tier. Security, irreversible actions, and a failed light attempt should still trigger a wait. Vague low-confidence prompts stay on `standard`. These are expectations for a readable heuristic, not guarantees or a benchmark. Any usage benefit depends on the authorized tier mapping and the option that actually runs.
