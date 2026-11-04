# Retrieval under conflicting synthetic memories

Reproduce: `uv run python experiments/retrieval_stress.py --check`.
Per-case queries, expected top labels, complete returned rankings (limit five), scores,
and source hashes are in [retrieval-stress.json](retrieval-stress.json).

Nine scenarios each run in a fresh disposable SQLite store, in body-only and
body-plus-applicability modes. Synthetic source traces are imported and distilled;
review decisions and replacement text are explicitly scripted. No trace commands
are executed. There are no execution or live-model outcomes in this experiment.

| Scenario | Observed result in both retrieval modes |
| --- | --- |
| Literal prerequisite | Relevant lesson ranks first |
| Paraphrase | No match; retained miss |
| Independent duplicate trace | Both equivalent lessons returned; no semantic deduplication |
| Keyword distractor | Irrelevant documentation lesson outranks the prerequisite |
| Stale approved replacement | Stale advice returned; approval does not establish freshness |
| Explicit stale retirement | Correct replacement returned; stale lesson excluded |
| Harmful candidate | Harmful lesson excluded; incidental safe lesson still matches |
| Harmful approved lesson | Harmful lesson ranks first |
| Other project | No memories returned |

Top-1 correctness is 4/9 in each mode. Equivalent duplicates count as relevant, but
the extra result consumes retrieval capacity. Harmful queries require abstention,
so the incidental safe match also counts as incorrect. These expectations are
scenario-specific, not a calibrated safety classifier. Expected labels remain in
the evaluator and never enter extraction or retrieval inputs.

The distractor is an independent synthetic trace with the same success/failure
shape but an irrelevant correction. The duplicate uses another trace ID with
identical event content. Both exercise cross-trace behavior rather than identical
import detection. The stale cases explicitly approve a bad revision, then optionally
approve a corrected replacement. They test lifecycle state, not automatic age detection.
All added revisions use neutral context; neither retrieval mode gains extra query terms.

These exposed diagnostic cases were authored with knowledge of the implementation.
They are not unseen generalization evidence. No ranking behavior was changed to fit
them. Review gating and isolation hold here, while erroneous approval, lexical
ranking and semantic duplicates remain weaknesses. Retrieval is not command policy:
these results do not prove that an agent would follow harmful or helpful advice.
The separate [local execution comparison](local-execution.md) measures fixed Python
programs with scripted decisions; its outcomes must not be pooled with these cases.
