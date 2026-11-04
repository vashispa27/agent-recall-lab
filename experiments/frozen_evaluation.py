"""Evaluate fixed independent synthetic tasks without changing retrieval behavior."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments/evaluation"


def load_dataset(directory=DATA):
    manifest = json.loads((directory / "manifest.json").read_text())
    if set(manifest) != {"traces.json", "tasks.json", "review.json"}:
        raise ValueError("Unexpected evaluation manifest members")
    for name, digest in manifest.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Frozen evaluation input changed: {name}")
    return {name: json.loads((directory / name).read_text()) for name in manifest}, manifest


def run():
    dataset, manifest = load_dataset()
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "memory.db")
        try:
            # Only source traces enter extraction; tasks and labels never enter the store.
            store.ingest_batch(dataset["traces.json"])
            store.distill()
            for memory in store.list_memories():
                if memory["trace_id"] in dataset["review.json"]["approved"]:
                    store.review(memory["id"], "approved")
            rows = []
            for case in dataset["tasks.json"]:
                hits = store.search(case["project"], case["query"])
                predicted = hits[0]["trace_id"] if hits else None
                rows.append(
                    {
                        **case,
                        "ranked_traces": [h["trace_id"] for h in hits],
                        "predicted_trace": predicted,
                        "correct": predicted == case["expected_trace"],
                    }
                )
        finally:
            store.close()
    return {
        "evidence_type": "synthetic_retrieval_only",
        "retriever": "unchanged lexical overlap; default limit 5",
        "input_sha256": manifest,
        "cases": rows,
        "by_category": {
            category: {
                "correct": sum(r["correct"] for r in rows if r["category"] == category),
                "total": sum(r["category"] == category for r in rows),
            }
            for category in sorted({r["category"] for r in rows})
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    output = ROOT / "experiments/results/frozen-evaluation.json"
    if args.check:
        if json.loads(output.read_text()) != result:
            raise SystemExit("Evaluation differs; investigate before replacing results")
        print("Frozen evaluation reproduced exactly")
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result["by_category"], indent=2))


if __name__ == "__main__":
    main()
