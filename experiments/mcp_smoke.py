"""Real stdio protocol checks against a disposable synthetic database."""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/mcp-smoke.json"


def payload(result):
    assert not result.isError, result.content
    return result.structuredContent or json.loads(result.content[0].text)


async def evaluate():
    source = ROOT / "examples/traces/generated-client.json"
    checks = {}
    with TemporaryDirectory() as directory:
        db = Path(directory) / "memory.db"
        store = Store(db)
        trace = load_trace(source)
        store.ingest(trace)
        store.distill()
        candidate = store.list_memories()[0]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "recall_lab.mcp_server", "--db", str(db), "--project", trace["project"]],
        )
        try:
            async with (
                stdio_client(parameters) as (read, write),
                ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as s,
            ):
                await s.initialize()
                tools = await s.list_tools()
                checks["retrieval_only_tools"] = {t.name for t in tools.tools} == {
                    "recall",
                    "inspect_source",
                }
                result = await s.call_tool("recall", {"query": "client"})
                checks["candidate_hidden"] = payload(result)["memories"] == []
                result = await s.call_tool("inspect_source", {"memory_id": candidate["id"]})
                checks["candidate_source_hidden"] = result.isError
                store.review(candidate["id"], "approved")
                result = await s.call_tool("recall", {"query": "client"})
                checks["approved_retrieved"] = [m["id"] for m in payload(result)["memories"]] == [
                    candidate["id"]
                ]
                result = await s.call_tool("inspect_source", {"memory_id": candidate["id"]})
                checks["source_provenance"] = bool(payload(result)["source_events"]) and (
                    payload(result)["extraction"]["source_sha256"]
                    == store.inspect_memory(candidate["id"], trace["project"])["extraction"][
                        "source_sha256"
                    ]
                )
                for limit in (0, 21):
                    result = await s.call_tool("recall", {"query": "client", "limit": limit})
                    checks[f"reject_limit_{limit}"] = result.isError
                result = await s.call_tool("recall", {"query": "client", "project": "other"})
                # SDK may ignore unknown fields, but cannot change the bound project.
                checks["cannot_override_project"] = result.isError or (
                    payload(result)["project"] == trace["project"]
                )
                other = dict(trace, id="other-trace", project="other")
                store.ingest(other)
                store.distill()
                foreign = store.list_memories()[0]
                store.review(foreign["id"], "approved")
                result = await s.call_tool("inspect_source", {"memory_id": foreign["id"]})
                checks["foreign_source_hidden"] = result.isError
                replacement = store.revise(
                    candidate["id"], trace["project"], "Replacement guidance", "New context"
                )
                store.review(replacement, "approved")
                result = await s.call_tool("recall", {"query": "client"})
                checks["supersession_visible_without_restart"] = payload(result)["memories"] == []
                result = await s.call_tool("inspect_source", {"memory_id": candidate["id"]})
                checks["rejected_source_hidden"] = result.isError
        finally:
            store.close()
    return {
        "evidence": "actual local stdio MCP calls; synthetic memory; no command execution or LLM",
        "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(evaluate())
    assert all(result["checks"].values()), result
    rendered = json.dumps(result, indent=2) + "\n"
    if args.check:
        assert OUTPUT.read_text() == rendered, "MCP results differ"
    else:
        OUTPUT.write_text(rendered)
    print(f"{len(result['checks'])} MCP protocol checks passed")


if __name__ == "__main__":
    main()
