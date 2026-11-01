"""Exercise CLI import boundaries using synthetic evidence in disposable databases."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from recall_lab.core import Store

ROOT = Path(__file__).resolve().parents[1]
VALID = "examples/traces/generated-client.json"
INVALID_VERSION = "examples/invalid/unsupported-version.json"
INVALID_EVENTS = "examples/invalid/duplicate-events.json"
CASES = [
    ("valid", [VALID], True, 1),
    ("identical_duplicates", [VALID, VALID], True, 1),
    ("invalid_version_rolls_back", [VALID, INVALID_VERSION], False, 0),
    ("duplicate_event_ids_roll_back", [VALID, INVALID_EVENTS], False, 0),
    ("conflicting_trace_rolls_back", [VALID, "conflict.json"], False, 0),
    ("malformed_json_rolls_back", [VALID, "malformed.json"], False, 0),
]


def run():
    rows = []
    for name, paths, expected_success, expected_count in CASES:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            conflict = json.loads((ROOT / VALID).read_text())
            conflict["events"][0]["text"] = "Different synthetic content"
            (temporary / "conflict.json").write_text(json.dumps(conflict))
            (temporary / "malformed.json").write_text('{"unfinished":')
            inputs = [ROOT / p if p.startswith("examples/") else temporary / p for p in paths]
            database = temporary / "memory.db"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "recall_lab.cli",
                    "--db",
                    str(database),
                    "ingest",
                    *map(str, inputs),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            store = Store(database)
            try:
                count = store.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
                memories = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            finally:
                store.close()
            success = result.returncode == 0
            rows.append(
                {
                    "case": name,
                    "inputs": paths,
                    "expected_success": expected_success,
                    "actual_success": success,
                    "expected_trace_count": expected_count,
                    "actual_trace_count": count,
                    "memory_count": memories,
                    "passed": success == expected_success
                    and count == expected_count
                    and memories == 0,
                }
            )
    sources = sorted({VALID, INVALID_VERSION, INVALID_EVENTS})
    digest = hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in sources)).hexdigest()
    return {
        "evidence_type": "local_cli_ingestion_only",
        "dataset_sha256": digest,
        "sources": sources,
        "derived_inputs": {
            "conflict.json": "Copy valid trace and replace first event text with Different synthetic content",
            "malformed.json": 'Literal {"unfinished":',
        },
        "cases": rows,
        "passed": sum(row["passed"] for row in rows),
        "total": len(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    if result["passed"] != result["total"]:
        raise SystemExit(json.dumps(result, indent=2))
    output = ROOT / "experiments/results/ingestion-contract.json"
    if args.check:
        if json.loads(output.read_text()) != result:
            raise SystemExit("Published ingestion results differ")
        print("Published ingestion results reproduced exactly")
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{result['passed']}/{result['total']} ingestion cases passed")


if __name__ == "__main__":
    main()
