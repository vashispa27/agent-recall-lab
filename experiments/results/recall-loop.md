# Controlled recall hooks

Reproduce with `uv run python experiments/recall_loop.py --check`.
The [per-case artifact](recall-loop.json) records six deterministic cases with ordered
recall, policy decision, and callback events. Its source hash identifies the unchanged
synthetic generated-client trace. Database IDs are normalized to source identity only
in the published artifact; the runtime audit exposes actual retrieved memory IDs.

`recall_lab.agent_loop.run_loop` binds all searches to one caller-specified project.
Disabled mode performs no retrieval. Task-start mode retrieves once and reuses those
hits; pre-command mode also refreshes retrieval using each caller-authored action's
context before consulting policy. An explicit boolean permits dispatch, denial skips
it, and callback exceptions stop the loop. Callers own the action list, policy, and
execution callback. No action is synthesized from memory. This integration uses the
local store API; the independently tested MCP transport remains available separately.

In this deliberately scripted demonstration, the policy permits a callback only if
retrieval returned a hit. The generic task query misses the approved lesson; the
specific pre-command query retrieves it for storefront. Only that case dispatches.
All three other-project cases abstain. This is a demonstration of hook placement and
lexical query sensitivity, **not execution success or evidence of prerequisite compliance**.
The callback merely appends an action name. No subprocess, fixture command text,
live LLM, or paid service is invoked. The policy neither interprets the correction nor
checks whether generation happened. Treating a hit as sufficient permission would be
inadequate for a real agent; an application must assess applicability and enforce its
own execution policy.

Tests cover ordered recall, blocked dispatch, project binding, context isolation from
policy mutation, strict boolean policy responses, validation, and stopping on errors.
Actual disposable command execution and broader retrieval quality evaluation remain
separate work. No improvement rate or token savings is claimed.
