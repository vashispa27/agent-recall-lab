"""Exercise capture, operator review and recall in separate local processes."""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_smoke import payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/native/codex-exec.jsonl"
OUTPUT = ROOT / "experiments/results/capture-recall.json"
PROJECT = "analytics"


async def recall_case(workspace, db, project, phase, candidate, expected):
    template = ROOT / "examples/integrations/codex/config.toml"
    config = tomllib.loads(template.read_text())["mcp_servers"]["project_recall"]
    args = [
        {"/absolute/path/to/memory.db": str(db), "storefront": project}.get(arg, arg)
        for arg in config["args"]
    ]
    parameters = StdioServerParameters(command=sys.executable, args=args, cwd=workspace)
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session,
    ):
        await session.initialize()
        result = await session.call_tool("recall", {"query": "analytics project pytest"})
        response = payload(result)
        assert response["project"] == project
        ids = [memory["id"] for memory in response["memories"]]
        assert ids == ([candidate] if expected else []), ids
        result = await session.call_tool("inspect_source", {"memory_id": candidate})
        assert result.isError == (not expected), result.content
        return {
            "phase": phase,
            "project": project,
            "retrieved_count": len(ids),
            "source_access": "denied" if result.isError else "allowed",
        }, None if result.isError else payload(result)


async def evaluate():
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    with TemporaryDirectory(prefix="capture-recall-") as workspace:
        db = Path(workspace) / "memory.db"

        def cli(*args):
            result = subprocess.run(
                [sys.executable, "-m", "recall_lab.cli", "--db", str(db), *args],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            return json.loads(result.stdout)

        capture = cli(
            "capture", str(FIXTURE), "--project", PROJECT, "--correction", "item2", "--synthetic"
        )
        assert capture == {"inserted": 1}, capture
        distill = cli("distill")
        assert distill == {"candidates_created": 1}, distill
        (candidate,) = cli("list")
        candidate_id = candidate["id"]
        inspected = cli("show", candidate_id, "--project", PROJECT)
        provenance = inspected["trace_provenance"]
        assert provenance["source_sha256"] == digest
        evidence_ids = [event["id"] for event in inspected["source_events"]]
        assert evidence_ids == ["item1", "item2", "item3"], evidence_ids
        assert "fixture-value" not in json.dumps(inspected)

        pending, _ = await recall_case(workspace, db, PROJECT, "candidate", candidate_id, False)
        # This scripted stand-in for operator review is a separate CLI invocation.
        decision = cli("review", candidate_id, "approved")
        assert decision["state"] == "approved"
        approved, source = await recall_case(workspace, db, PROJECT, "approved", candidate_id, True)
        assert source["trace_provenance"] == provenance
        assert source["source_events"] == inspected["source_events"]
        foreign, _ = await recall_case(workspace, db, "unrelated", "approved", candidate_id, False)
        assert not (Path(workspace) / "sentinel").exists()
        return {
            "evidence": "synthetic export, scripted operator review, actual CLI and stdio MCP",
            "dataset_sha256": digest,
            "capture": capture,
            "distill": distill,
            "evidence_item_ids": evidence_ids,
            "trace_command_sentinel_created": False,
            "cases": [pending, approved, foreign],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(evaluate())
    if args.check:
        assert json.loads(OUTPUT.read_text()) == result, "Capture and recall results differ"
    else:
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print("Three capture and recall cases passed")


if __name__ == "__main__":
    main()
