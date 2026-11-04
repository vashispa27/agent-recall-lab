# Reviewed applicability retrieval comparison

Reproduce with `uv run python experiments/applicability_comparison.py --check`.
Per-case outputs and the synthetic source byte hash are in
[applicability-comparison.json](applicability-comparison.json). The runner contains
all queries, expectations and the exact reviewed replacement body/context.

`Store.search(..., include_applicability=True)` optionally includes approved revision
applicability in the lexical token set. The score remains query-token overlap divided
by query-token count, with memory-ID tie breaking and default limit five. The default
remains body-only; CLI, MCP and controlled-loop behavior are unchanged. Context is
searchable text, not a command restriction or enforced applicability predicate.

This is a deliberately constructed synthetic mechanism ablation over one memory:
body-only gets 4/6 expected hit/abstention decisions; body plus context gets 5/6.
Two literal task/command context matches are recovered, while a negated query becomes
a false positive. Both modes retrieve the literal body query and abstain for an
unrelated query and a different project. Proposed revision context is excluded before
approval; approval atomically retires the old lesson. The test checks these boundaries.

These are demonstration cases written alongside the implementation, not unseen
accuracy estimates. No frozen evaluation inputs or labels were modified, no semantic
paraphrase capability was added, and these results do not resolve its three known
paraphrase misses. No commands from traces, model calls or local execution experiments
occur here. A retrieved hit does not show an agent followed it. A single-memory
hit/abstention comparison cannot measure ranking quality among distractors, duplicates,
stale approved lessons or harmful approved advice. Those remain separate evaluations.
