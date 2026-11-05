# Capture, review and recall across processes

```bash
uv sync --locked --extra dev
uv run python experiments/capture_recall.py --check
```

The runner imports the bundled [invented Codex JSONL export](../../examples/native/codex-exec.jsonl)
into a temporary SQLite database using the real CLI. Separate CLI processes distill
one candidate and inspect its three linked events. The check verifies the exact
export SHA-256 and confirms the fixture credential value is absent from the inspection
response. The runner then explicitly approves the displayed candidate ID through the
review CLI.

Each case starts a fresh local stdio MCP process and initializes a new client session.
All three query for `analytics project pytest` and try to inspect the same candidate ID.
The approved case also compares the returned source events and provenance against the
CLI inspection.

| Case | Retrieved lessons | Source access |
| --- | ---: | --- |
| Analytics, awaiting review | 0 | Denied |
| Analytics, after explicit approval | 1 | Allowed |
| Unrelated project, after approval | 0 | Denied |

The [per-case results](capture-recall.json) include the export hash and evidence item IDs.
The fixture's command text stays data. Its sentinel file did not appear in the disposable
workspace.

The subprocesses and protocol exchanges ran locally. The export, command outcomes and
correction are invented, and the runner scripts the operator's approval decision. The
experiment exercises persistence across MCP sessions and the project boundary. It makes
no live model calls and measures neither agent instruction following nor downstream
task success. Separate [disposable execution cases](local-execution.md) measure real
fixture commands under a scripted policy.
