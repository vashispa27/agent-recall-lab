# Memory foundation findings

The canonical trace pipeline is reproducible, but there is no evidence yet that
retrieving its lessons improves agent task success. The current product accepts
invented canonical traces only; native Claude/Codex adapters, MCP tools and a
recall-before-command integration are absent.

## Reproduced evidence

| Evidence | Observation | Interpretation |
| --- | --- | --- |
| Local CLI ingestion | 6/6 cases match expected status and durable row counts | Batch rollback and duplicate handling work for these fixtures |
| Synthetic retrieval | 5/6 positive queries rank the expected lesson first | Lexical overlap recovers most curated lessons |
| Synthetic retrieval abstention | 2/2 negative queries return no lesson | Wrong-project and unrelated-query cases abstain |
| Paraphrase | Expected generated-client lesson; no result | Vocabulary mismatch remains a retrieval failure |
| Unit and integration tests | 30 passed | Covered contracts pass; this is not a task-success metric |

Per-case outputs and source digests are retained in
[ingestion-contract.json](ingestion-contract.json) and
[retrieval-baseline.json](retrieval-baseline.json). No result files were changed
when reproducing these findings. CI also checks exact reproduction of both artifacts.

## Architecture and trust boundaries

The CLI lazily loads JSON files into a single SQLite transaction. JSON parsing
rejects duplicate keys; the packaged schema rejects unsupported versions and
unknown fields. Python checks unique event IDs. Validation copies input before
applying a limited credential-pattern redactor. Identical redacted payloads are
idempotent; conflicting trace IDs abort the batch.

Distillation retains an explicit correction between a failed command and a later
successful command in the same trace. Each candidate stores its source trace ID
and three event IDs. Temporal adjacency is a heuristic, not proof that the
correction caused success. Command strings remain evidence text throughout.

Only explicit candidate approval admits a memory to search. The benchmark's
review policy approves five ordinary lessons and leaves a poisoned correction
unapproved. The extractor does not detect poisoning. An unsafe approval could
therefore expose harmful text. Project filtering is an exact string comparison,
not an authenticated multi-user authorization boundary.

Retrieval tokenizes the query and approved lesson text, ranks shared-token
coverage, and breaks ties by memory ID. Zero-overlap lessons are omitted.
Evidence IDs accompany returned lessons, but no running agent consumes them yet.

## Reproduce

From the repository root:

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python experiments/retrieval_baseline.py --check
uv run python experiments/ingestion_contract.py --check
```

The ingestion experiment executes the known local CLI against disposable SQLite
databases. It never executes fixture command text. Retrieval is a deterministic
synthetic evaluation, not scripted agent replay, task-command execution, or a live
LLM experiment. No paid services or model calls were used.

## Limits and remaining work

The eight traces and eight retrieval queries form a small development dataset.
Fixture wording was clarified during initial development; it is not a held-out
benchmark. Preserve the paraphrase miss and freeze independent cases before
comparative retrieval tuning. Two abstentions do not establish broad isolation
or robustness to adversarial queries.

Redaction is incomplete and the accepted schema intentionally excludes real
session imports. Native-format adapters need explicit supported subsets and
provenance before such imports can be evaluated. Review currently supports only
one approval or rejection, without edits, supersession or applicability rules.

A controlled disposable execution fixture and recall integration are needed to
measure actual prerequisite ordering separately from retrieval. Live-model
instruction following, task success and token savings remain unmeasured.
