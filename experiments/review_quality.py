"""Deterministic review lifecycle checks over synthetic evidence; no command execution."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/review-quality.json"


def run():
    cases = []
    sources = ["generated-client", "poisoned-correction"]
    hashes = {}
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "memory.db")
        try:
            for name in sources:
                path = ROOT / f"examples/traces/{name}.json"
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
                store.ingest(load_trace(path))
            store.distill()
            memories = store.list_memories()
            poison = next(m for m in memories if m["trace_id"] == "poisoned-correction")
            old = next(m for m in memories if m["trace_id"] == "generated-client")
            cases.append(
                {
                    "case": "poison-still-proposed",
                    "passed": "upload" in poison["body"],
                    "negative_outcome": "Extractor does not detect unsafe correction",
                }
            )
            store.review(poison["id"], "rejected")
            store.review(old["id"], "approved")
            cases.append(
                {
                    "case": "rejected-poison-excluded",
                    "passed": all(
                        m["id"] != poison["id"]
                        for m in store.search(old["project"], "upload tests")
                    ),
                }
            )
            new = store.revise(
                old["id"],
                old["project"],
                "Generate current client before tests",
                "Only integration tests using the generated client",
            )
            cases.append(
                {
                    "case": "revision-gated",
                    "passed": [m["id"] for m in store.search(old["project"], "client")]
                    == [old["id"]],
                }
            )
            store.review(new, "approved")
            cases.append(
                {
                    "case": "stale-source-retired",
                    "passed": [m["id"] for m in store.search(old["project"], "client")] == [new],
                }
            )
            cases.append(
                {"case": "project-isolation", "passed": not store.search("billing", "client")}
            )
            cases.append({"case": "reimport-preserves-review", "passed": store.distill() == 0})
        finally:
            store.close()
    return {
        "evidence_type": "synthetic retrieval and actual local SQLite operations",
        "sources_sha256": hashes,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    encoded = json.dumps(result, indent=2) + "\n"
    if not all(case["passed"] for case in result["cases"]):
        raise SystemExit("Review contract failed")
    if args.check:
        if OUTPUT.read_text() != encoded:
            raise SystemExit("Artifact differs; reproduce and inspect")
    else:
        OUTPUT.write_text(encoded)
    print(f"{len(result['cases'])} review quality cases passed")


if __name__ == "__main__":
    main()
