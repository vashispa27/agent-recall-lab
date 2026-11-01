# Canonical trace import contract

The CLI imports a batch in one SQLite transaction. Six disposable-database cases
passed: a valid trace, identical duplicate inputs, and rollback after an unsupported
schema version, duplicate event IDs, conflicting content, or malformed JSON.
[Per-case observations and fixture digest](ingestion-contract.json) preserve the
expected and actual success status, durable trace counts, and memory counts.

Reproduce from the repository root:

```bash
uv sync --locked --extra dev
uv run python experiments/ingestion_contract.py --check
uv run pytest -q
```

The inputs are invented canonical traces from `examples/traces` and
`examples/invalid`. The conflict is derived by changing the valid trace's first
event text; the malformed input is a fixed incomplete JSON object. The script
records these derivations and the digest of its source fixture files. It invokes
only the known Python CLI, never command text from traces, and uses temporary
SQLite databases. It does not distill or approve any memory.

This is actual local CLI execution evidence about ingestion, not agent task
execution or live LLM behavior. The rejection cases intentionally return a failing
CLI status. The existing synthetic retrieval baseline is unchanged: 5/6 positive
top-1 hits and 2/2 correct abstentions. Its paraphrase failure remains unresolved.

The schema accepts only synthetic version-1 evidence and rejects unknown fields;
event ID uniqueness is additionally checked in Python. Redaction is still a
limited pattern-based baseline, not a comprehensive credential detector. Schema
validation does not prove that a correction is safe or that an agent followed it.
