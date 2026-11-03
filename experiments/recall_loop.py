"""Scripted hook demonstration. No shell execution or LLM decisions."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.agent_loop import Action, run_loop
from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]


def run():
    fixture = ROOT / "examples/traces/generated-client.json"
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "memory.db")
        try:
            store.ingest(load_trace(fixture))
            store.distill()
            memory = store.list_memories()[0]
            store.review(memory["id"], "approved")
            cases = []
            for project in ("storefront", "other-project"):
                for mode in ("disabled", "task_start", "pre_command"):
                    dispatched = []
                    audit = run_loop(
                        store,
                        project,
                        "Investigate a development task",
                        [Action("integration-check", "integration tests generated client")],
                        # A deliberately scripted gate: evidence presence permits dispatch.
                        # It does not interpret a lesson or prove the prerequisite happened.
                        lambda action, hits: bool(hits),
                        lambda action, target=dispatched: (
                            target.append(action.name) or "scripted callback"
                        ),
                        mode,
                    )
                    # Stable public artifacts use source identity instead of database UUIDs.
                    for entry in audit:
                        if "memory_ids" in entry:
                            entry["memory_ids"] = ["generated-client" for _ in entry["memory_ids"]]
                    cases.append(
                        {"project": project, "mode": mode, "dispatched": dispatched, "audit": audit}
                    )
        finally:
            store.close()
    return {
        "evidence_type": "synthetic_retrieval_with_scripted_callback",
        "dataset_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    output = ROOT / "experiments/results/recall-loop.json"
    if args.check:
        if json.loads(output.read_text()) != result:
            raise SystemExit("Recall loop result differs")
        print("Recall loop results reproduced exactly")
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
