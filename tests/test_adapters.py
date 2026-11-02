import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from recall_lab.adapters import adapt_trace, load_native_trace
from recall_lab.core import Store

ROOT = Path(__file__).resolve().parents[1]


def fixture(format):
    return json.loads((ROOT / f"examples/native/{format}.json").read_text())


@pytest.mark.parametrize(
    "format,evidence",
    [("claude", ["c2:0", "c3:0", "c5:0"]), ("codex", ["item1", "item2", "item3"])],
)
def test_source_links_review_gate_and_redaction(tmp_path, format, evidence):
    source = fixture(format)
    original = copy.deepcopy(source)
    trace = adapt_trace(source, format)
    assert source == original
    assert len(trace["provenance"]["source_sha256"]) == 64
    store = Store(tmp_path / "memory.db")
    try:
        assert store.ingest(trace)
        assert not store.ingest(load_native_trace(ROOT / f"examples/native/{format}.json", format))
        assert store.distill() == 1
        memory = store.list_memories()[0]
        assert json.loads(memory["evidence"]) == evidence
        assert store.search(trace["project"], "run") == []
        store.review(memory["id"], "approved")
        assert store.search(trace["project"], "run")
        assert store.search("other-project", "run") == []
        payload = store.db.execute("SELECT payload FROM traces").fetchone()[0]
        assert "synthetic-native-secret" not in payload
    finally:
        store.close()


@pytest.mark.parametrize("format", ["claude", "codex"])
@pytest.mark.parametrize(
    "mutation",
    [
        "non_synthetic",
        "unknown",
        "duplicate",
        "bad_annotation",
        "no_correction",
        "unsupported",
        "bad_type",
    ],
)
def test_fail_closed_and_never_infer_corrections(format, mutation):
    source = fixture(format)
    if mutation == "non_synthetic":
        source["synthetic"] = 1
    elif mutation == "unknown":
        source["private_metadata"] = "password=do-not-echo"
    elif mutation == "duplicate":
        source["records"].append(source["records"][0])
    elif mutation == "bad_annotation":
        source["correction_ids"] = ["absent"]
    elif mutation == "no_correction":
        source["correction_ids"] = []
        trace = adapt_trace(source, format)
        assert not any(e["action"] == "correction" for e in trace["events"])
        return
    elif mutation == "unsupported":
        source["records"][0]["type"] = "unknown"
    else:
        source["records"] = [None]
    with pytest.raises(ValueError, match="Unsupported") as error:
        adapt_trace(source, format)
    assert "do-not-echo" not in str(error.value)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "boolean", "mismatch", "dangling", "orphan", "duplicate_result", "bad_block"],
)
def test_claude_requires_matched_explicit_outcomes(mutation):
    source = fixture("claude")
    if mutation == "missing":
        source["exit_codes"].pop("tool1")
    elif mutation == "boolean":
        source["exit_codes"]["tool1"] = True
    elif mutation == "mismatch":
        source["exit_codes"]["tool1"] = 0
    elif mutation == "dangling":
        source["records"].pop()
    elif mutation == "orphan":
        source["records"].pop(0)
    elif mutation == "duplicate_result":
        result = copy.deepcopy(source["records"][1])
        result["uuid"] = "duplicate-result"
        source["records"].insert(2, result)
    else:
        source["records"][2]["message"]["content"] = [1]
    with pytest.raises(ValueError, match="Unsupported"):
        adapt_trace(source, "claude")


@pytest.mark.parametrize(
    "code,status", [(None, "completed"), (True, "failed"), (1, "completed"), (0, "in_progress")]
)
def test_codex_rejects_missing_or_inconsistent_outcomes(code, status):
    source = fixture("codex")
    source["records"][0]["item"].update(exit_code=code, status=status)
    with pytest.raises(ValueError, match="Unsupported"):
        adapt_trace(source, "codex")


@pytest.mark.parametrize("format", ["claude", "codex"])
def test_cli_atomic_native_import_and_duplicate_keys(tmp_path, format):
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"synthetic": true, "synthetic": true}')
    db = tmp_path / "memory.db"
    command = [
        sys.executable,
        "-m",
        "recall_lab.cli",
        "--db",
        str(db),
        "ingest",
        "--format",
        format,
        str(ROOT / f"examples/native/{format}.json"),
    ]
    failed = subprocess.run([*command, str(invalid)], capture_output=True, check=False)
    assert failed.returncode != 0
    store = Store(db)
    assert store.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0
    store.close()
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"inserted": 1}
