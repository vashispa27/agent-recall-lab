# Synthetic native-format subsets

These invented fixtures use selected Claude message/tool blocks and Codex exec event
shapes. They are not captured sessions or evidence that either agent followed a lesson.
The enclosing `synthetic`, `id`, `project`, `correction_ids`, and Claude `exit_codes`
fields are lab annotations, not native fields. No command text is executed.

```bash
uv run recall --db /tmp/recall-claude-demo.db ingest --format claude examples/native/claude.json
uv run recall --db /tmp/recall-codex-demo.db ingest --format codex examples/native/codex.json
uv run python experiments/native_adapters.py --check
```

Use a fresh database path for an isolated demo. Both inputs create candidates only after
`distill`; inspection and explicit approval are still required for retrieval.

## Supported contract

- Claude: records with `uuid`, `type` (`user` or `assistant`), and `message` containing
  matching `role` and `content`. Content is a string or nonempty list of text,
  assistant `tool_use` (`Bash` with only `input.command`), or user `tool_result` blocks.
  Results must reference a preceding tool ID exactly once. All calls need results.
  An annotation supplies the integer exit code for each call; `is_error` must agree.
  Native `is_error` alone does not supply a numeric exit status.
- Codex: only `item.completed` records containing `agent_message` or
  `command_execution`. Commands require a non-null integer exit code, string command
  and aggregated output, and `completed` (zero) or `failed` (nonzero) status.
- Correction annotations name text-record IDs (Claude UUID or Codex item ID).
  Unannotated user text is a prompt; unannotated assistant text is a response.
  Message prose never automatically becomes a correction.
- Unknown fields, other tools/events, duplicate identities or JSON keys, missing
  results, contradictory outcomes and unused annotations are rejected. There is no
  silent skipping of unsupported input. Full native JSONL files, streaming records,
  arbitrary tool output blocks and genuine sessions are not supported.

## Provenance and mapping

A canonical trace retains the source envelope's SHA-256 over UTF-8 JSON serialized
with sorted keys and compact separators. This identifies synthetic fixture content,
not authenticity. Raw input is not stored; canonical event text is redacted.

Claude canonical event IDs are `uuid:block-index`; a command event belongs to the
result record and incorporates the command from its matched `tool_use_id`.
Codex event IDs equal item IDs. Evidence references these canonical IDs. The source
fixture and hash let a reviewer inspect annotations and the original tool pairing.
The annotations themselves remain untrusted evidence.

Shape references: [Claude tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
for message content blocks; [Codex exec event definitions](https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs)
for completed command and message items. These references describe the selected
shapes; this adapter makes no claim of compatibility with every native export version.
No upstream implementation code is copied.
