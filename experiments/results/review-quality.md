# Review quality and replacement boundaries

Reproduce: `uv run python experiments/review_quality.py --check`.
[Per-case results and source hashes](review-quality.json) record six deterministic
checks over two existing invented traces. The script uses a disposable local SQLite
database. No trace commands or live model calls execute.

All six contract checks pass: poisoned correction remains proposed, manual rejection
excludes it, replacement text remains gated until approval, approval removes the old
lesson from retrieval, project isolation holds, and repeated extraction preserves review.
The poison case is a retained negative result: ordered successful-looking evidence
still cannot establish safety. The evaluator explicitly chooses rejection.

`recall revise ID --project PROJECT --body TEXT --applicability CONTEXT` creates a
candidate revision of an approved lesson. Inspect it with `recall show`, then explicitly
approve or reject it with `recall review`. Approval atomically marks the predecessor
rejected and activates the replacement. Rejected revisions leave the original active.
Concurrent competing replacements cannot both be approved. Source evidence remains
inspectable, while revision text is attributed to review rather than extraction.

Applicability is descriptive reviewer context returned with revised search results;
it does not enforce command or environment matching. Existing memories have no inferred
applicability. Superseded lessons use the existing rejected state; the revision link
records which replacement retired them. Distinct traces with equivalent lessons are
still separate candidates, without semantic deduplication. These checks demonstrate
store behavior, not agent compliance, automatic poison detection, execution improvement,
or generalization to unseen tasks. Subsequent [recall integration findings](recall-integration-findings.md)
cover the MCP transport and controlled recall hooks separately.
