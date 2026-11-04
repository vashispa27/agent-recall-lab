# Retrieval evidence and failure analysis

Approved memory can recover literal prerequisites, but lexical overlap cannot establish
relevance, freshness or safety. Adding reviewed applicability text recovers two literal
context matches in a constructed ablation and introduces a negation false positive.
Conflicting-memory scenarios retain the same failures in both modes.

## Results and denominators

| Evaluation | Body only | Body plus applicability | What is scored |
| --- | --- | --- | --- |
| [Fixed synthetic tasks](frozen-evaluation.json) | 9/12 | Not evaluated | Expected top source, or abstention |
| [Applicability ablation](applicability-comparison.json) | 4/6 | 5/6 | Expected hit or abstention |
| [Conflicting memories](retrieval-stress.json) | 4/9 | 4/9 | Expected top label, or abstention |

These denominators must not be pooled: tasks, review decisions and scoring rules differ.
The applicability comparison has one approved replacement, so it measures matching,
not ranking among competing memories. Stress revisions use neutral context, so that
comparison supplies no added query vocabulary. It does not show context is universally
ineffective. The fixed evaluation was not rerun with contextual retrieval as an ablation.

## Exact retrieval configuration

All runners create disposable SQLite stores. Only exact-project, approved memories
enter ranking. Queries and searchable text are lowercased and tokenized with
`[a-z0-9_]+` into unique sets. Score is intersecting token count divided by query-token
count. Only positive scores return; there is no tuned confidence threshold. Results
sort by descending score and then ascending memory ID, with limit five. There is no
stemming, embedding, negation handling, age penalty or semantic deduplication.

The default searches body text. The opt-in `include_applicability=True` unions reviewed
revision context into searchable text; CLI, MCP and controlled-loop callers retain the
default. Context is descriptive text rather than an enforced policy. Approval of a
replacement atomically supersedes its old memory, but approval cannot verify truth.

## Retained failures

- All three fixed-set paraphrases miss; literal cases pass 3/3.
- Context matching recovers task and command vocabulary, but also matches a negated query.
- Separate trace IDs with equivalent content consume two result positions.
- A keyword distractor outranks the prerequisite; deterministic ID tie breaking is not relevance.
- Stale approved advice returns until explicitly retired by an approved replacement.
- A harmful approved lesson ranks first. Excluding a proposed harmful candidate still
  leaves an incidental safe hit where the scenario expects abstention.
- Project isolation and proposed-memory exclusion hold in these fixtures; neither
  establishes that approved content is safe or suitable for every action.

## Provenance and evidence boundaries

The [fixed input manifest](../evaluation/manifest.json) freezes source, task and review
bytes. Only traces enter extraction; labels stay in the evaluator. See the
[dataset account](../evaluation/README.md). The ablation and stress JSON artifacts retain
source hashes and per-case queries, expectations and rankings; their runners define
scripted review decisions. All sources are invented, and evaluators were specified
with knowledge of the implementation. These are exposed diagnostic regression cases,
not unseen generalization evidence or independent human judgments.

The separate [execution comparison](local-execution.md) runs fixed repository-authored
Python programs in temporary directories with isolated Python and ten-second timeouts.
Only approved same-project pre-command recall passes its prerequisite check; eleven
negative controls fail. A scripted policy recognizes a fixed memory ID. This proves
ordering in that fixture, not an agent's understanding or compliance. The
[controlled loop](recall-loop.md) is scripted replay, while the
[MCP check](mcp-smoke.md) exercises actual local protocol calls. Neither is a live LLM
experiment. Trace command text is never executed. No model calls, token savings, costs,
real-world success rates or safety guarantees were measured. Live-model evidence is
unavailable without established credentials and an explicit spending cap.

## Reproduce

From the repository root with Python 3.11+ and uv:

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python experiments/retrieval_baseline.py --check
uv run python experiments/frozen_evaluation.py --check
uv run python experiments/applicability_comparison.py --check
uv run python experiments/retrieval_stress.py --check
uv run python experiments/local_execution.py --check
uv run python experiments/recall_loop.py --check
uv run python experiments/mcp_smoke.py --check
```

Checks compare retained artifacts instead of silently replacing failures. No new
retrieval tuning accompanies this synthesis. Stronger evidence requires independently
specified unseen cases, more prerequisites and applications, and a separately measured
agent integration. Semantic ranking, conflict resolution, freshness checks and enforcement
of action constraints remain open work; current retrieval should support review rather
than authorize arbitrary execution.
