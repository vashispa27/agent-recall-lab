"""Reproducible lexical retrieval evaluation. No model or shell commands execute."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
APPROVED = {"generated-client", "python-path", "package-manager", "database-schema", "environment"}


def run() -> dict:
    cases = json.loads((ROOT / "experiments/cases.json").read_text())
    fixture_paths = sorted((ROOT / "examples/traces").glob("*.json"))
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "memory.db")
        try:
            for path in fixture_paths:
                store.ingest(load_trace(path))
            candidates = store.distill()
            for memory in store.list_memories():
                if memory["trace_id"] in APPROVED:
                    store.review(memory["id"], "approved")
            rows = []
            for case in cases:
                hits = store.search(case["project"], case["query"])
                predicted = hits[0]["trace_id"] if hits else None
                rows.append(
                    {
                        **case,
                        "predicted_trace": predicted,
                        "correct": predicted == case["expected_trace"],
                    }
                )
        finally:
            store.close()
    source_paths = fixture_paths + [ROOT / "experiments/cases.json"]
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in source_paths)).hexdigest()
    positives = [r for r in rows if r["expected_trace"] is not None]
    negatives = [r for r in rows if r["expected_trace"] is None]
    return {
        "evidence_type": "synthetic_retrieval_only",
        "dataset_sha256": digest,
        "trace_count": len(fixture_paths),
        "candidate_count": candidates,
        "approved_count": len(APPROVED),
        "cases": rows,
        "positive_top1_accuracy": sum(r["correct"] for r in positives) / len(positives),
        "negative_abstention_accuracy": sum(r["correct"] for r in negatives) / len(negatives),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    output = ROOT / "experiments/results/retrieval-baseline.json"
    if args.check:
        if json.loads(output.read_text()) != result:
            raise SystemExit("Published baseline differs; investigate and regenerate intentionally")
        print("Published baseline reproduced exactly")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
