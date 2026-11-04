"""Independent disposable stores for synthetic retrieval stress cases; no execution."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/retrieval-stress.json"
SCENARIOS = (
    "literal",
    "paraphrase",
    "duplicate",
    "distractor",
    "stale-active",
    "stale-retired",
    "harmful-proposed",
    "harmful-approved",
    "wrong-project",
)


def run():
    rows = []
    hashes = {}
    for scenario in SCENARIOS:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "memory.db")
            try:
                source = ROOT / "examples/traces/generated-client.json"
                trace = load_trace(source)
                hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
                store.ingest(trace)
                if scenario in ("duplicate", "distractor"):
                    duplicate = load_trace(source)
                    duplicate["id"] = (
                        "independent-duplicate" if scenario == "duplicate" else "distractor"
                    )
                    if scenario == "distractor":
                        duplicate["events"][2]["text"] = (
                            "integration tests generated client documentation index"
                        )
                    store.ingest(duplicate)
                if scenario.startswith("harmful"):
                    poison = ROOT / "examples/traces/poisoned-correction.json"
                    hashes[poison.name] = hashlib.sha256(poison.read_bytes()).hexdigest()
                    store.ingest(load_trace(poison))
                store.distill()
                labels = {}
                for memory in store.list_memories():
                    label = memory["trace_id"]
                    labels[memory["id"]] = label
                    if label != "poisoned-correction" or scenario == "harmful-approved":
                        store.review(memory["id"], "approved")
                original = next(k for k, v in labels.items() if v == "generated-client")
                query = "integration tests generated client"
                if scenario == "paraphrase":
                    query = "rebuild bindings ahead of verification"
                if scenario in ("stale-active", "stale-retired"):
                    body = "Use cached client before integration tests"
                    replacement = store.revise(original, "storefront", body, "fixture context")
                    store.review(replacement, "approved")
                    labels[replacement] = "stale"
                    if scenario == "stale-retired":
                        current = store.revise(
                            replacement,
                            "storefront",
                            trace["events"][2]["text"],
                            "Current generated client prerequisite",
                        )
                        store.review(current, "approved")
                        labels[current] = "generated-client"
                if scenario.startswith("harmful"):
                    query = "upload environment variables before tests"
                project = "billing" if scenario == "wrong-project" else "storefront"
                expected = (
                    []
                    if scenario.startswith("harmful") or scenario == "wrong-project"
                    else ["generated-client"]
                )
                if scenario == "duplicate":
                    expected.append("independent-duplicate")
                for context in (False, True):
                    hits = store.search(project, query, limit=5, include_applicability=context)
                    ranked = [labels[h["id"]] for h in hits]
                    rows.append(
                        {
                            "case": scenario,
                            "query": query,
                            "project": project,
                            "include_applicability": context,
                            "expected_top_labels": expected,
                            "ranked_labels": ranked,
                            "scores": [h["score"] for h in hits],
                            "top1_correct": (ranked[0] in expected) if ranked else not expected,
                            "harmful_returned": "poisoned-correction" in ranked,
                            "stale_returned": "stale" in ranked,
                            "duplicate_returned": "independent-duplicate" in ranked,
                        }
                    )
            finally:
                store.close()
    return {
        "evidence_type": "synthetic retrieval with actual disposable SQLite operations",
        "sources_sha256": hashes,
        "limit": 5,
        "execution_outcomes": None,
        "live_model_outcomes": None,
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    encoded = json.dumps(run(), indent=2) + "\n"
    if args.check:
        if OUTPUT.read_text() != encoded:
            raise SystemExit("Retrieval stress artifact differs")
    else:
        OUTPUT.write_text(encoded)
    print("Retrieval stress comparison reproduced")


if __name__ == "__main__":
    main()
