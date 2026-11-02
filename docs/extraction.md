# Evidence-linked candidate extraction

`Store.distill()` defaults to `CorrectionRuleExtractor`, provider ID
`explicit-correction-v1`. It yields an immutable `CandidateProposal(body, evidence)`
for each explicit correction with an earlier failed command and a later successful
command. It picks the nearest matching commands around the correction. Evidence is
an ordered tuple of those three source event IDs. This is a deterministic ordering
rule; a later success does not establish that a lesson caused it or is safe.

A `CandidateExtractor` has a stable `provider_id` and `extract(trace)` method returning
proposals. A local implementation can be passed to `store.distill(provider)`.
No LLM provider, credentials, network calls, or paid extraction path is included.
The interface receives a copy of a validated, redacted canonical trace, without
evaluation queries or expected labels.

The store validates proposals against its original source snapshot. References must
exist in that trace and follow failure/correction/success order. The store assigns
project, trace ID, stable candidate identity and `candidate` state itself. Provider
output cannot approve a memory or assign it to a different project. Proposed text
is redacted before storage. Invalid proposals, conflicting content for an existing
correction, and provider exceptions roll back the entire distillation batch.
Previously reviewed memories remain unchanged. Providers run as trusted local Python
code; this contract is data validation, not a sandbox for hostile provider code.

For each new memory, `memory_extractions` stores provider identity and SHA-256 of the
validated, redacted canonical trace (sorted-key compact JSON). This differs from a
native adapter's hash of its synthetic source envelope. Hashes identify content;
they do not authenticate a session or prove an outcome. Existing databases acquire
the metadata table automatically. Existing memories retain their states and IDs;
metadata stays null when no original extraction record exists, rather than claiming
a provider created them retroactively. Repeating identical proposals is idempotent.
A differing proposal for the same correction raises an error and needs review.

## Inspect before approval

```bash
uv run recall ingest examples/traces/generated-client.json
uv run recall distill
uv run recall list
# Substitute the candidate ID shown by list:
uv run recall show <candidate-id> --project storefront
uv run recall review <candidate-id> approved
```

`show` returns memory state, body, source events, optional adapter provenance, and
extraction metadata. It requires the matching project even for candidate or rejected
memories. The project parameter is a local data-scoping boundary, not multi-user
authentication. Rejected memories remain absent from retrieval. Source text and
proposed lessons are untrusted: inspection must assess relevance and safety, not
merely check that source IDs exist.

[Reproducible checks](../experiments/results/extraction-contract.md) retain the
negative result that a successful-looking poisoned correction passes this rule.
Editing, supersession and explicit applicability fields are not implemented yet.
