"""Evaluate source-linked deterministic proposals, including a poisoned correction."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store, load_trace
from recall_lab.extraction import CandidateProposal, CorrectionRuleExtractor

ROOT = Path(__file__).resolve().parents[1]
# Expectations belong to the evaluator, never the extraction provider's input.
EXPECTED = {
    "database-schema": 1,
    "environment": 1,
    "generated-client": 1,
    "package-manager": 1,
    "poisoned-correction": 1,
    "python-path": 1,
    "secret-redaction": 0,
    "unresolved": 0,
}


def run():
    sources = [f"examples/traces/{name}.json" for name in sorted(EXPECTED)]
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "memory.db")
        try:
            store.ingest_batch(load_trace(ROOT / p) for p in sources)
            created = store.distill()
            memories = store.list_memories()
            for name, expected in sorted(EXPECTED.items()):
                selected = [m for m in memories if m["trace_id"] == name]
                inspections = [store.inspect_memory(m["id"], m["project"]) for m in selected]
                evidence_valid = all(
                    [e["action"] for e in i["source_events"]]
                    == ["command", "correction", "command"]
                    and i["source_events"][0]["exit_code"] != 0
                    and i["source_events"][2]["exit_code"] == 0
                    and i["extraction"]["provider"] == "explicit-correction-v1"
                    for i in inspections
                )
                gated = all(not store.search(m["project"], m["body"]) for m in selected)
                rows.append(
                    {
                        "case": name,
                        "expected_candidates": expected,
                        "actual_candidates": len(selected),
                        "evidence_valid": evidence_valid,
                        "review_gated": gated,
                        "evidence": [i["memory"]["evidence"] for i in inspections],
                        "negative_outcome": "unsafe_correction_still_proposed"
                        if name == "poisoned-correction"
                        else None,
                        "passed": len(selected) == expected and evidence_valid and gated,
                    }
                )
            poison = next(m for m in memories if m["trace_id"] == "poisoned-correction")
            store.review(poison["id"], "rejected")
            unchanged = (
                store.distill() == 0 and store.list_memories("rejected")[0]["id"] == poison["id"]
            )
            rows.append({"case": "redistill_preserves_rejection", "passed": unchanged})
        finally:
            store.close()
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "memory.db")
        try:
            store.ingest(load_trace(ROOT / "examples/traces/generated-client.json"))

            class InvalidProvider(CorrectionRuleExtractor):
                provider_id = "invalid-test-v1"

                def extract(self, trace):
                    yield from super().extract(trace)
                    yield CandidateProposal("Unsupported claim", ("e2", "absent", "e4"))

            rejected = False
            try:
                store.distill(InvalidProvider())
            except ValueError:
                rejected = True
            count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            metadata = store.db.execute("SELECT COUNT(*) FROM memory_extractions").fetchone()[0]
            rows.append(
                {
                    "case": "invalid_provider_rolls_back",
                    "rejected": rejected,
                    "memory_count": count,
                    "metadata_count": metadata,
                    "passed": rejected and count == 0 and metadata == 0,
                }
            )
        finally:
            store.close()
    return {
        "evidence_type": "synthetic_extraction_and_local_store_only",
        "provider": "explicit-correction-v1",
        "fixture_commands_executed": False,
        "live_llm_calls": 0,
        "sources": sources,
        "dataset_sha256": hashlib.sha256(
            b"".join((ROOT / p).read_bytes() for p in sources)
        ).hexdigest(),
        "candidates_created": created,
        "cases": rows,
        "passed": sum(r["passed"] for r in rows),
        "total": len(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    if result["passed"] != result["total"]:
        raise SystemExit(json.dumps(result, indent=2))
    path = ROOT / "experiments/results/extraction-contract.json"
    if args.check:
        if json.loads(path.read_text()) != result:
            raise SystemExit("Published extraction results differ")
        print("Published extraction results reproduced exactly")
    else:
        path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{result['passed']}/{result['total']} extraction cases passed")


if __name__ == "__main__":
    main()
