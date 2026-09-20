# Auto model router — examples

These examples show the expected tier **and confirm gate** from the provider-agnostic prototype rubric in [`demo/classify.py`](demo/classify.py). Hosts should always emit a one-line suggestion. They wait for confirmation only when the gate requires it. Policy background: [`docs/boundary-gated-confirms.md`](docs/boundary-gated-confirms.md).

| # | Real-world task | Expected tier | Gate | Why |
|---:|---|---|---|---|
| 1 | Rename the `customer_id` field to `account_id` in one config file | **fast** | **auto_continue** | Clear, bounded, reversible single-file edit; not near a boundary. |
| 2 | Summarize the incident timeline in this issue into five bullets | **fast** | **auto_continue** | Short, bounded summarization. |
| 3 | Follow these steps to add a logging line to `main.py` | **fast** | **auto_continue** | The procedure is already specified. |
| 4 | Apply the same null-check pattern across a few files in the API client | **standard** | **auto_continue** | Multi-file known pattern with strong standard fit; local/reversible. |
| 5 | Wire up a CRUD endpoint using the existing handler pattern | **standard** | **auto_continue** | Routine feature work with a clear local shape. |
| 6 | Rename the helper and apply the same null-check pattern across a few files | **standard** | **confirm** | Mixed rename + multi-file signals sit near the fast/standard boundary. |
| 7 | Debug why checkout authentication fails intermittently in production | **reasoning** | **hard_gate** | Unknown root cause **and** auth/security risk. |
| 8 | Design the architecture for a multi-tenant billing system | **reasoning** | **confirm** | Architecture and tradeoff judgment are central. |
| 9 | Review this auth change for XSS, credential leaks, and unsafe redirects | **reasoning** | **hard_gate** | Security-sensitive review must not be under-provisioned. |
| 10 | Prove a novel consensus algorithm and redesign the distributed store | **max** | **confirm** | Formal reasoning plus a large, ambiguous redesign. |

## Canonical gate examples

### Clear rename → auto-continue

```text
User: Rename the customer_id field to account_id in one config file.
Agent: Auto continues on fast — clear bounded rename. Switch Cursor picker to
       <your-fast-model> / low effort if the current model is heavier than needed.
```

### Auth / secrets → hard-gate

```text
User: Review this auth change for XSS, credential leaks, and unsafe redirects.
Agent: Auto suggests reasoning — security-sensitive review must not be under-provisioned.
       Switch Cursor picker to <your-reasoning-model> / high effort (current pick is
       lighter than needed). Confirm the switch, or override: fast, standard, reasoning, or max.
```

### Near-boundary → confirm

```text
User: Rename the helper and apply the same null-check pattern across a few files.
Agent: Auto suggests standard — mixed rename + multi-file signals sit near a tier boundary.
       Confirm to run, or override: fast, standard, reasoning, or max.
User: confirm
Agent: [maps standard and starts]
```

On Cursor, fill in [`integrations/cursor-tier-map.example.json`](integrations/cursor-tier-map.example.json) so those lines name **your** picker labels. The portable skill keeps placeholders; it does not hard-code vendor model names and it cannot read Cursor usage meters.

For mixed wording such as “draft a prototype redesign we can throw away,” reversible cues can bias toward a lighter **tier**. If those cues still mix adjacent families, the **gate** stays confirm. Security, irreversible actions, and a failed light attempt should still hard-gate or stop for confirm. These are expectations for a readable heuristic, not guarantees or a benchmark. Any usage benefit depends on the authorized tier mapping and the option that actually runs.
