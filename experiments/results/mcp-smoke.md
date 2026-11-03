# MCP transport checks

Reproduce with `uv sync --locked --extra dev` and
`uv run python experiments/mcp_smoke.py --check`.
[Per-case results](mcp-smoke.json) record 11 passing checks and the synthetic source hash.
The experiment launches an actual local stdio server subprocess and uses the official
Python MCP SDK client to initialize, discover tools, and call them. No fixture command
is executed, no model is called, and no agent behavior or task improvement is measured.

The server binds its database and project at startup. `recall` returns only approved
lessons; `inspect_source` exposes their source events and extraction metadata. Candidate,
rejected and foreign-project sources are unavailable through this transport. Review
and supersession use the existing local Store API in the experiment; the transport
has no review or write tools. Approval and supersession are observed without restarting.
Invalid limits are returned as protocol tool errors. An extra project argument cannot
change the configured project (the SDK may ignore unknown arguments).

Run a server from this repository with:

```bash
uv run python -m recall_lab.mcp_server --db /absolute/path/memory.db --project storefront
```

Configure an MCP host to launch that command with this repository as its working
directory. Standard output is reserved for protocol traffic. The SDK is pinned to
its maintained v1 compatibility line (`mcp>=1.28,<2`), resolved in the lockfile;
see the [official SDK documentation](https://py.sdk.modelcontextprotocol.io/v1/).

Memory and source text remain untrusted data even after review. The startup project
binding is an integration boundary, not authentication against someone with filesystem
access to the database. Only stdio is supported here; there is no remote service or
command runner. A host must explicitly call recall before acting. This experiment
does not establish that any host or LLM follows a lesson. Lexical retrieval limitations,
manual review dependence, and descriptive-only applicability remain unchanged.
