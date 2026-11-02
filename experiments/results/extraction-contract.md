# Extraction contract and retained failure

Reproduce with `uv run python experiments/extraction_contract.py --check`.
[Per-case results](extraction-contract.json) record the dataset hash, evidence IDs,
candidate counts and rejection/rollback outcomes. Inputs are the eight invented
canonical traces; expectations stay in the evaluator, outside provider input.

Ten contract checks pass. The default provider produces six candidates with ordered
failure/correction/success references. The unresolved trace and credential-only
trace produce none. Every candidate remains unavailable for retrieval before review.
Re-extraction preserves a rejection, and an invalid provider proposal rolls back
both earlier candidates and their extraction metadata.

**Retained negative result:** the poisoned correction still produces a candidate.
The synthetically successful follow-up does not make its instruction safe. This
experiment explicitly rejects that candidate as a controlled reviewer decision;
it does not demonstrate automatic poison detection. Contract success is not a
memory-quality score or evidence of improved agent outcomes.

The [provider interface and inspection documentation](../../docs/extraction.md)
describe source hashes, legacy metadata handling, and review requirements. Unit tests
also cover provider input mutation, foreign or reordered evidence, candidate conflicts,
provider exceptions, restart persistence and project-scoped CLI inspection.

All evidence here is synthetic extraction and actual local SQLite operations.
No trace commands or live LLM calls are executed, and no token savings, causal
improvement or generalization to real sessions is claimed. The ordering heuristic
can connect unrelated failures and successes; human review remains necessary.
