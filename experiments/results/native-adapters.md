# Synthetic adapter boundary checks

Reproduce with `uv run python experiments/native_adapters.py --check`.
[Per-case JSON](native-adapters.json) includes the dataset hash and source hashes.
The two [invented native-format inputs](../../examples/native/README.md) supply explicit
correction annotations; Claude numeric outcomes are also explicit fixture annotations.

Six cases pass: both adapters import and deduplicate, produce one evidence-linked
candidate, enforce approval before retrieval, and isolate projects; each rejects an
unsupported record and an unmatched correction annotation. Unit tests additionally
exercise ambiguous outcomes, malformed blocks, duplicate identities, missing tool
results, credential redaction, and atomic CLI rollback on a duplicate-key input.

This is deterministic conversion and local database evidence. It is not a native
agent integration, execution benchmark, or live LLM experiment. No fixture command is
executed. The narrow parser rejects real exports containing additional metadata or
unsupported records rather than silently discarding them. Broader native compatibility,
authentic source verification and correction extraction from unannotated sessions
remain unimplemented. Successful-looking poisoned lessons still require human review.
