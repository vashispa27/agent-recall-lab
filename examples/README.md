# Synthetic evidence, not real agent runs

Eight canonical traces exercise corrections, failure without resolution, credential
redaction, and a malicious correction. `claude` and `codex` identify simulated sources;
the files are already canonical and do not prove native integration compatibility.

Each correction follows a failed command and precedes a simulated successful command.
That ordering supports candidate extraction, but does not prove causality or safety.
The poisoned correction deliberately passes that naive rule and must remain unapproved.

Experiment queries and expected source IDs live in experiments/cases.json, never inside
trace inputs. Five trace IDs are explicitly approved by the benchmark's synthetic reviewer.
This reviewer is curated ground truth, not a production review policy.
The paraphrase query is an intentional lexical-retrieval weakness. Do not silently remove it.
This initial set is a development benchmark, not an untouched held-out test set.
A separate test set must be frozen before comparison experiments.

The [version-1 canonical schema](../src/recall_lab/schemas/trace.schema.json) requires
`schema_version: 1`, `synthetic: true`, nonblank trace/project/harness identifiers,
and a nonempty event list. Event IDs must be unique within a trace. Only command
events carry an integer `exit_code`; booleans are rejected. Unknown fields are
rejected to prevent silently persisting unvalidated metadata. Event text is
redacted before storage without modifying the caller's input.

`invalid/` contains invented unsupported-version and duplicate-event examples for
rejection checks. Keep these separate from `traces/`, which supplies the retrieval
benchmark. Loading a batch containing either invalid example must leave no new
traces behind. The JSON loader also rejects duplicate object keys.
