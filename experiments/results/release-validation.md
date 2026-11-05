# Agent Recall Lab v0.1.0 validation

Agent Recall Lab turns an explicitly selected local session export into a proposed
lesson with inspectable evidence. After an operator approves the lesson, a later
session can retrieve it from the same project through local MCP tools.

## Run the lifecycle demo

From the repository root with Python 3.11+ and uv:

```bash
uv sync --locked --extra dev
uv run python experiments/capture_recall.py --check
```

The demo creates a disposable SQLite database, imports an invented Codex exec
export through the CLI, distills a lesson, inspects its evidence, and scripts the
operator's explicit approval. Fresh stdio MCP sessions query the database before
and after approval and from another project. [Lifecycle method and results](capture-recall.md)

For your own project, use the [capture and review instructions](../../docs/capture.md)
and the [Codex CLI setup](../../docs/codex-recall.md). Capture takes a caller-selected
finished export in the supported single-turn format. Review the linked evidence before
approval and bind MCP to the same project key.

## Architecture

1. **Capture.** The CLI validates the selected JSONL export, converts supported events
   to the canonical trace format, redacts recognized secrets, and stores the trace
   with its source digest in SQLite.
2. **Distill and review.** The deterministic provider proposes lessons linked to source
   events. The operator can inspect those events and record a review decision.
   Approving a replacement supersedes its prior memory in the same transaction.
3. **Recall.** A project-bound MCP process searches approved lessons in SQLite and
   exposes their supporting evidence. The default lexical ranking uses query-token
   overlap. Codex project instructions cue tool use at task start, before relevant
   commands, and after relevant failures. Tool calls are chosen by the client.

## What the checks show

| Evidence | Observed result |
| --- | --- |
| [Capture to recall](capture-recall.json) | The approved lesson and matching source evidence returned in a fresh same-project MCP session. Pending and cross-project queries returned zero lessons and source access was denied. The fixture command sentinel stayed absent. |
| [MCP smoke test](mcp-smoke.json) | Eleven local protocol checks exercised project binding, review gating, evidence inspection, and request validation. |
| [Fixed synthetic retrieval](frozen-evaluation.json) | Nine of twelve cases met the expected top-source or abstention criterion. All three paraphrases missed. |
| [Applicability ablation](applicability-comparison.json) and [stress cases](retrieval-stress.json) | Applicability text changed the ablation from four of six to five of six and introduced a negation false positive. Both configurations passed four of nine stress cases, with duplicate, stale, and harmful approved results retained. |
| [Controlled replay](recall-loop.json) | Scripted callbacks tested task-start and pre-command retrieval and recorded the order of recall and policy decisions. |
| [Disposable local execution](local-execution.json) | Real fixture programs passed only with approved same-project pre-command recall under a scripted policy. Eleven controls failed the prerequisite check. |

The capture demo and retrieval evaluations use invented source material. The
execution comparison runs fixed repository-authored Python programs. Trace command
text stays data throughout. The [dataset notes](../../examples/README.md) and
[fixed input manifest](../evaluation/manifest.json) describe provenance and separate
evaluation labels from extraction inputs.

## Reproduce all checks

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
for experiment in experiments/*.py; do
  uv run python "$experiment" --check || exit 1
done
```

Each experiment compares its output against a retained artifact, including negative
cases. The tests and runners use local disposable state.

## Handoff limits

Capture is manual and bounded. Continuous collection, broad native-session import,
a review UI, and cloud forwarding are outside this release. The redactor recognizes
a limited set of secret patterns. Project binding scopes tool access, while filesystem
permissions protect the database itself.

Approval is a review decision. The retriever can still surface stale, irrelevant,
or harmful approved text. Semantic matching, automatic freshness and conflict checks,
and enforced command policy remain unimplemented. The Codex integration is
instruction-driven. The checks make no live model calls, so tool selection,
instruction following, task improvement, and token savings remain unmeasured.
