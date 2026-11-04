# Fixed synthetic retrieval evaluation

These invented tasks and source traces are separate from the development corpus in
`examples/traces` and `experiments/cases.json`. They introduce translation catalogs,
asset indexes and queue schemas. Task expectations were specified before the first
run of this evaluator; the lexical retriever was unchanged. This is a small manually
authored diagnostic set, not an independently collected or statistically representative
benchmark. The implementation's existing behavior was already known when specifying it.

`traces.json` is the only extraction input. `review.json` specifies synthetic human
review decisions. `tasks.json` holds queries, categories and expected source identities
outside extraction. Every trace has invented failure/correction/success events; those
events establish ordering only. Their text is never executed. The unsafe correction
remains proposed, so the review-gate case tests exclusion, not automatic safety judgment.

`manifest.json` freezes exact input bytes using SHA-256. The runner checks all three
members before ingestion. Hashes detect accidental edits, not malicious replacement
of the manifest. Preserve this set for comparisons; use development cases for tuning.
Once results are inspected or used to select retrieval changes, this becomes an exposed
regression set and cannot support claims of unseen generalization. New unseen evidence
requires separately specified cases.

Run `uv run python experiments/frozen_evaluation.py --check` from the repository root.
The checked-in per-case results include complete ranked source IDs, expected labels,
input hashes and category counts. No LLM, command execution, token or cost outcomes
are measured here. Stale lessons, semantic duplicates and harmful approved retrieval
remain outside this set's coverage.
