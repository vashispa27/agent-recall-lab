"""Actual disposable Python execution with scripted recall decisions; no trace execution."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from recall_lab.agent_loop import Action, run_loop
from recall_lab.core import Store, load_trace

ROOT = Path(__file__).resolve().parents[1]
# These programs are authored here, never loaded from retrieved text or trace commands.
GENERATE = "from pathlib import Path; Path('client.txt').write_text('fixture-client-v1')"
CHECK = """from pathlib import Path
import sys
p = Path('client.txt')
ok = p.is_file() and p.read_text() == 'fixture-client-v1'
print('client ready' if ok else 'generated client missing')
sys.exit(0 if ok else 1)
"""


def run():
    fixture = ROOT / "examples/traces/generated-client.json"
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "memory.db")
        try:
            store.ingest(load_trace(fixture))
            store.distill()
            memory_id = store.list_memories()[0]["id"]
            for reviewed in (False, True):
                if reviewed:
                    store.review(memory_id, "approved")
                for project in ("storefront", "other-project"):
                    for mode in ("disabled", "task_start", "pre_command"):
                        with tempfile.TemporaryDirectory() as workspace:
                            commands = []

                            def execute(name, program, target=commands, directory=workspace):
                                result = subprocess.run(
                                    [sys.executable, "-I", "-c", program],
                                    cwd=directory,
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    check=False,
                                )
                                record = {
                                    "program": name,
                                    "exit_code": result.returncode,
                                    "stdout": result.stdout,
                                    "stderr": result.stderr,
                                }
                                target.append(record)
                                return record

                            def policy(action, hits):
                                # Recognize only the reviewed fixture ID. Never interpret
                                # or execute the lesson's command text.
                                if any(hit["id"] == memory_id for hit in hits):
                                    execute("generate", GENERATE)
                                return True

                            audit = run_loop(
                                store,
                                project,
                                "Investigate a development task",
                                [Action("check", "integration tests generated client")],
                                policy,
                                lambda _: execute("check", CHECK),
                                mode,
                            )
                            for entry in audit:
                                if "memory_ids" in entry:
                                    entry["memory_ids"] = [
                                        "generated-client" for _ in entry["memory_ids"]
                                    ]
                            cases.append(
                                {
                                    "reviewed": reviewed,
                                    "project": project,
                                    "mode": mode,
                                    "commands": commands,
                                    "passed": commands[-1]["exit_code"] == 0,
                                    "audit": audit,
                                }
                            )
        finally:
            store.close()
    return {
        "evidence_type": "actual_local_execution_with_scripted_policy",
        "dataset_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "programs_sha256": hashlib.sha256((GENERATE + "\n" + CHECK).encode()).hexdigest(),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    output = ROOT / "experiments/results/local-execution.json"
    if args.check:
        if json.loads(output.read_text()) != result:
            raise SystemExit("Local execution results differ")
        print("12 local execution cases reproduced exactly")
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Wrote {len(result['cases'])} local execution cases")


if __name__ == "__main__":
    main()
