# Import one local session export

On macOS or Linux, use `recall capture` to import an explicitly selected, finished
`codex exec --json` export. Review the file before import and store it outside version
control. The command reads one local file and writes canonical evidence to SQLite.
Capture does not invoke Codex, run commands from the export, or watch session directories.

```bash
scratch=$(mktemp -d)
uv run recall --db "$scratch/memory.db" capture examples/native/codex-exec.jsonl \
  --project analytics --correction item2 --synthetic
uv run recall --db "$scratch/memory.db" distill
uv run recall --db "$scratch/memory.db" list
```

Use `--synthetic` for invented data. For an existing real export, omit that flag.
Choose a stable project key and use the same key for inspection and recall. The importer
uses that explicit key and does not discover the project from paths in the export.
Each `--correction ITEM_ID` marks a completed agent message you selected as correction
evidence. With no annotations, import preserves the messages as responses. Distillation
and approval are separate actions. Inspect a candidate with `show ID --project PROJECT`
before approving it with `review ID approved`.

The supported subset is one UTF-8, newline-terminated turn that starts with
`thread.started` and `turn.started` and ends with `turn.completed`. Completed
items must be agent messages or command executions with consistent numeric exit
codes and status. Intermediate `item.started` and `item.updated` records are
discarded. Unsupported completed items, failed turns, multi-turn logs, and internal
rollout files are outside this subset. The input limit is 1 MiB and 2,000 records.
The importer rejects malformed data before inserting a trace.

Evidence links retain completed item IDs and the SHA-256 of the exact export bytes.
The project key and thread ID determine trace identity. Reimporting identical data and
annotations is idempotent. Changed bytes or annotations for the same project and thread
conflict with the stored trace. Only normalized, redacted event text is stored, and the
baseline redactor covers a limited set of credential patterns. Review exports for secrets
and personal data before ingestion.

See [capture checks](../experiments/results/capture-import.md) for fixture provenance and
reproduction.
