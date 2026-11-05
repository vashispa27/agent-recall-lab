# Local export import checks

Reproduce with `uv run pytest -q tests/test_capture.py`. The invented JSONL export
in [examples/native](../../examples/native/codex-exec.jsonl) wraps the existing
synthetic Codex correction sequence in a single turn. It adds an inert command sentinel
and an invented credential marker. Each test uses a fresh temporary directory.

| Case | Observed result |
| --- | --- |
| Explicit import and identical repeat | One trace inserted, then zero |
| Evidence and redaction | Three source item IDs and exact input hash retained; credential marker redacted |
| Untrusted command | Sentinel file absent |
| Review and database reopen | Candidate excluded before approval; approved result available after reopen |
| Other project | Approved result excluded |
| Unannotated message | No correction inferred and no candidate created |
| Invalid correction and changed annotations | Command annotation rejected; changed annotation conflicts with stored trace |
| Truncated, missing completion, unknown record, duplicate JSON key | Each rejected with zero stored traces |
| Byte and record limits | Each exceeded limit rejected with zero stored traces |
| Symlink and FIFO | Both rejected |

The checks exercise a real local CLI import and SQLite persistence using synthetic
session data. Live session export compatibility and live-model behavior remain unmeasured.
