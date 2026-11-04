# Fixed evaluation: lexical retrieval

The unchanged lexical retriever correctly answers 9 of 12 manually specified synthetic
cases. All three paraphrase cases fail. Literal queries pass 3/3, abstentions 2/2,
project isolation 2/2, the single distractor 1/1 and proposed-unsafe exclusion 1/1.
These small counts describe these inputs only.

Reproduce from the repository root:

```bash
uv sync --locked --extra dev
uv run python experiments/frozen_evaluation.py --check
```

[Per-case results](frozen-evaluation.json) retain all misses, ranked source IDs and
exact input hashes. [Dataset provenance and boundaries](../evaluation/README.md)
explain the pre-evaluation task specification and separation from extraction inputs.
No retrieval code or thresholds changed to improve this result.

The literal cases recover the catalog, asset-index and queue-schema lessons. The
three natural task descriptions do not recover their intended lesson. This supports
investigating applicability and paraphrases; it does not establish a general success
rate or demonstrate that an agent follows retrieved advice. The isolation cases and
proposed unsafe lesson pass through existing project and review filters. They do not
measure harm from an approved incorrect lesson. The distractor result is only one case.

This is retrieval-only evidence: no scripts from traces execute, no local action
outcomes are scored and no live model is called. The existing disposable execution
comparison remains a separate experiment. Semantic duplicate, stale-memory and
approved harmful-retrieval comparisons remain incomplete. After inspection these
cases are exposed regression data, not an unseen holdout for future tuning claims.
