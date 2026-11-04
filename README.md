# Agent Recall Lab

Can a coding agent avoid repeating a mistake when a previous session's lesson is
retrieved **before** it runs a command?

A small, local-first memory service and evaluation lab inspired by
[Agent Beacon](https://github.com/Asymptote-Labs/agent-beacon). Original implementation;
not affiliated with Asymptote Labs. Python 3.11+, SQLite, reproducible synthetic data.

## What works today

- Schema-validated canonical traces, atomic batch import, lightweight credential redaction,
  and duplicate detection.
- Explicitly synthetic [Claude/Codex format subsets](examples/native/README.md) with
  source hashes, matched tool results, and strict rejection of unsupported records.
- SQLite storage of traces, evidence-linked candidates, and explicitly reviewed memories.
- An [evidence-linked extraction interface](docs/extraction.md), deterministic provider,
  durable provider/source metadata, and project-scoped source inspection; **not LLM extraction**.
- Project-scoped keyword retrieval of approved memory only.
- Review-gated revisions with atomic supersession and inspectable applicability context.
- Project-bound [stdio MCP recall and source tools](experiments/results/mcp-smoke.md),
  tested with real local protocol calls.
- A [controlled recall loop](experiments/results/recall-loop.md) with task-start and
  pre-command hooks, explicit policy decisions, and an ordered retrieval audit trail.
- Eight synthetic traces, separate evaluation queries, tests, and a retrieval baseline.

A [disposable execution comparison](experiments/results/local-execution.md) runs real
local Python checks with scripted prerequisite decisions. Full native-session ingestion
is not implemented yet.
The controlled loop uses scripted callbacks; it does not establish live-agent behavior.

## Run

```bash
uv sync --locked --extra dev
uv run recall ingest examples/traces/*.json
uv run recall distill
uv run recall list
# Inspect a candidate and its source events before approving its displayed ID:
uv run recall show <candidate-id> --project storefront
uv run recall review <candidate-id> approved
uv run recall search --project storefront 'integration tests generated client'
uv run pytest -q
uv run python experiments/retrieval_baseline.py
```

`recall ingest` validates every input and imports the whole batch atomically. An invalid
file or conflicting trace ID rolls back new rows; identical redacted traces are skipped.
Direct store ingestion applies the same validation and redaction. See the
[canonical schema](src/recall_lab/schemas/trace.schema.json) and
[reproducible import checks](experiments/results/ingestion-contract.md).

Every trace is invented. Fixture commands are evidence text and never executed.
The redactor is a small baseline, not a comprehensive secret detector.

## Architecture

```mermaid
flowchart LR
  T[Synthetic traces] --> V[Validate and redact]
  V --> S[SQLite traces]
  S --> C[Correction candidates]
  C --> R[Explicit review]
  R --> M[Approved memory]
  M --> Q[Project-scoped retrieval]
```

## Experiments and limits

[Retrieval findings](experiments/results/retrieval-findings.md) compare exact configurations,
ablations and retained failures, with separate retrieval and execution denominators.

[Conflicting-memory stress cases](experiments/results/retrieval-stress.md) retain
duplicate, distractor, stale and harmful approved retrieval failures.

[Reviewed applicability comparison](experiments/results/applicability-comparison.md)
adds opt-in context matching, with a retained negation false positive.

[Fixed evaluation](experiments/results/frozen-evaluation.md) adds a separate hashed
synthetic task set with per-case rankings and retained paraphrase misses.

[Recall integration findings](experiments/results/recall-integration-findings.md) connect
the protocol, hook and disposable execution evidence, with a runnable comparison and
an explicit account of what remains unmeasured.

[Review quality checks](experiments/results/review-quality.md) demonstrate replacement
review gating, stale-lesson retirement, and explicit poison rejection. Applicability
is descriptive context, not an enforced command policy.

[Extraction checks](experiments/results/extraction-contract.md) retain the unsafe
correction that passes the ordering rule and verify provider failure rollback.

[Adapter boundary checks](experiments/results/native-adapters.md) reproduce synthetic
conversion and review gating; they do not establish native-agent behavior.

[Foundation findings](experiments/results/foundation-findings.md) explain the current
architecture, reproduced evidence, failure cases, and missing integrations.

[Baseline results](experiments/results/retrieval-baseline.md) measure retrieval against
curated synthetic lessons. They do not establish that an LLM follows those lessons,
that tests pass more often, or that tokens are saved. Evaluation ground truth is
kept outside trace files. See [dataset notes](examples/README.md).

License: MIT. No upstream code has been copied.
