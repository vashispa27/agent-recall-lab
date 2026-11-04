"""Synthetic lexical ablation using explicit reviewed context; no execution or LLM."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/results/applicability-comparison.json"


def run():
    source = ROOT / "examples/traces/generated-client.json"
    cases = [
        ("body-match", "storefront", "Generate current client", True),
        ("task-context", "storefront", "checkout contract verification", True),
        ("command-context", "storefront", "verify_contract.py", True),
        ("negated-context", "storefront", "avoid checkout contract verification", False),
        ("wrong-project", "billing", "checkout contract verification", False),
        ("unrelated", "storefront", "certificate renewal", False),
    ]
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "memory.db")
        try:
            store.ingest(load_trace(source))
            store.distill()
            old = store.list_memories()[0]
            store.review(old["id"], "approved")
            replacement = store.revise(
                old["id"],
                old["project"],
                "Generate current client before tests",
                "For checkout contract verification before verify_contract.py",
            )
            # Proposed context must remain invisible in both modes.
            gated = not store.search(
                old["project"], "verify_contract.py", include_applicability=True
            )
            store.review(replacement, "approved")
            for name, project, query, expected in cases:
                for contextual in (False, True):
                    hits = store.search(project, query, include_applicability=contextual)
                    rows.append(
                        {
                            "case": name,
                            "project": project,
                            "query": query,
                            "expected_hit": expected,
                            "mode": "body+applicability" if contextual else "body",
                            "ranked_ids": [h["id"] for h in hits],
                            "correct": bool(hits) == expected,
                        }
                    )
        finally:
            store.close()
    return {
        "evidence_type": "synthetic retrieval only",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "proposed_context_excluded": gated,
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    encoded = json.dumps(run(), indent=2) + "\n"
    if args.check:
        if OUTPUT.read_text() != encoded:
            raise SystemExit("Applicability comparison differs")
    else:
        OUTPUT.write_text(encoded)
    print("Applicability comparison reproduced")


if __name__ == "__main__":
    main()
