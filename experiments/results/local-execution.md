# Disposable prerequisite execution comparison

Reproduce from the repository root:

```bash
uv sync --locked --extra dev
uv run python experiments/local_execution.py --check
uv run pytest -q tests/test_local_execution.py
```

The [per-case results](local-execution.json) contain 12 cases, subprocess exit codes,
stdout/stderr, command order, recall audit and source/program hashes. Each case gets a
fresh temporary directory. Two fixed, repository-authored Python programs generate a
small client file and check its exact contents. Python runs in isolated mode with a
10-second timeout per process. No shell is invoked and no trace command is executed.
This fixture models prerequisite ordering; it is not a real application integration suite.

The synthetic source is `examples/traces/generated-client.json`. Its extracted lesson
starts proposed; six cases run before explicit approval, and six after. The policy
recognizes only this fixture's memory ID and dispatches the fixed generator when retrieved.
It always permits the check. Retrieval supplies evidence to a scripted decision; it does
not translate arbitrary lesson text into executable code. Project isolation and review
gating are measured alongside the execution outcomes.

| Memory state / project | Disabled | Task-start | Pre-command |
| --- | --- | --- | --- |
| Proposed / storefront | fail | fail | fail |
| Proposed / other-project | fail | fail | fail |
| Approved / storefront | fail | fail | pass |
| Approved / other-project | fail | fail | fail |

All 11 failures exit 1 with `generated client missing`. The single passing case records
generate exit 0 followed by check exit 0 with `client ready`. Task-start retrieval misses
because the deliberately generic task query has no relevant lexical overlap; pre-command
context names integration tests and the generated client. Negative controls remain in
the artifact, including the approved cross-project abstention and proposed-memory cases.
No improvement rate over realistic tasks can be inferred from one constructed prerequisite.

This is **actual local execution with a scripted policy**, combined with synthetic
retrieval evidence. It is neither live LLM behavior nor proof that an agent understood
or followed a lesson. There were no LLM calls or token measurements. The runner uses
controlled disposable fixtures, not an operating-system security sandbox; it should not
be extended to execute untrusted trace contents. Broader retrieval quality, paraphrases,
distractors and real application tasks remain unmeasured by this comparison.
