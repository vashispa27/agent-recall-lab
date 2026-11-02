"""Reproduce synthetic adapter import, provenance, and review boundaries."""

import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.adapters import adapt_trace
from recall_lab.core import Store

ROOT = Path(__file__).resolve().parents[1]


def run():
    rows = []
    sources = []
    for format in ["claude", "codex"]:
        path = f"examples/native/{format}.json"
        sources.append(path)
        source = json.loads((ROOT / path).read_text())
        trace = adapt_trace(source, format)
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "memory.db")
            try:
                inserted = store.ingest(trace)
                duplicate = store.ingest(trace)
                created = store.distill()
                candidate = store.list_memories()[0]
                gated = not store.search(trace["project"], "run")
                store.review(candidate["id"], "approved")
                retrieved = bool(store.search(trace["project"], "run"))
                isolated = not store.search("unrelated-project", "run")
                rows.append(
                    {
                        "case": format + "_import_review",
                        "inserted": inserted,
                        "duplicate_inserted": duplicate,
                        "candidates": created,
                        "evidence": json.loads(candidate["evidence"]),
                        "source_sha256": trace["provenance"]["source_sha256"],
                        "review_gated": gated,
                        "approved_retrieved": retrieved,
                        "project_isolated": isolated,
                        "passed": inserted
                        and not duplicate
                        and created == 1
                        and gated
                        and retrieved
                        and isolated,
                    }
                )
            finally:
                store.close()
        for name in ["unknown_record", "unmatched_correction"]:
            invalid = copy.deepcopy(source)
            if name == "unknown_record":
                invalid["records"][0]["type"] = "unsupported"
            else:
                invalid["correction_ids"] = ["missing"]
            rejected = False
            try:
                adapt_trace(invalid, format)
            except ValueError:
                rejected = True
            rows.append({"case": format + "_" + name, "rejected": rejected, "passed": rejected})
    return {
        "evidence_type": "synthetic_conversion_and_local_store_only",
        "fixture_commands_executed": False,
        "live_llm_calls": 0,
        "sources": sources,
        "dataset_sha256": hashlib.sha256(
            b"".join((ROOT / p).read_bytes() for p in sources)
        ).hexdigest(),
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
    path = ROOT / "experiments/results/native-adapters.json"
    if args.check:
        if json.loads(path.read_text()) != result:
            raise SystemExit("Published adapter results differ")
        print("Published adapter results reproduced exactly")
    else:
        path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{result['passed']}/{result['total']} adapter cases passed")


if __name__ == "__main__":
    main()
