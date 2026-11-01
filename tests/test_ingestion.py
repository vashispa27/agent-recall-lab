import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from recall_lab.core import TRACE_SCHEMA, Store, load_trace, validate_trace

ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "examples/traces/generated-client.json"


@pytest.mark.parametrize(
    "change",
    [
        lambda t: t.update(schema_version=2),
        lambda t: t.update(schema_version=True),
        lambda t: t.pop("schema_version"),
        lambda t: t.update(synthetic=False),
        lambda t: t.update(synthetic=1),
        lambda t: t.update(project="  "),
        lambda t: t.update(events=[]),
        lambda t: t.update(unknown="token=secret"),
        lambda t: t["events"][0].update(id=" "),
        lambda t: t["events"][0].update(exit_code=0),
        lambda t: t["events"][1].pop("exit_code"),
        lambda t: t["events"][1].update(exit_code=True),
        lambda t: t["events"][1].update(extra="password=secret"),
    ],
)
def test_store_rejects_invalid_inputs_without_loader(tmp_path, change):
    trace = json.loads(VALID.read_text())
    change(trace)
    store = Store(tmp_path / "memory.db")
    try:
        with pytest.raises(ValueError, match="Invalid trace") as error:
            store.ingest(trace)
        assert "secret" not in str(error.value)
        assert store.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0
    finally:
        store.close()


def test_schema_and_invalid_examples():
    Draft202012Validator.check_schema(TRACE_SCHEMA)
    for path in (ROOT / "examples/traces").glob("*.json"):
        validate_trace(json.loads(path.read_text()))
    for path in (ROOT / "examples/invalid").glob("*.json"):
        with pytest.raises(ValueError):
            load_trace(path)
    for value in [None, [], "text", 1]:
        with pytest.raises(ValueError):
            validate_trace(value)


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        VALID.read_text().replace(
            '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,'
        )
    )
    with pytest.raises(ValueError, match="Duplicate JSON"):
        load_trace(path)


def test_direct_ingestion_redacts_without_mutating_source(tmp_path):
    trace = json.loads(VALID.read_text())
    trace["events"][0]["text"] = "token=synthetic-sensitive-value"
    original = copy.deepcopy(trace)
    store = Store(tmp_path / "memory.db")
    try:
        assert store.ingest(trace)
        assert trace == original
        raw = store.db.execute("SELECT payload FROM traces").fetchone()[0]
        assert "synthetic-sensitive-value" not in raw
        assert "[REDACTED]" in raw
        assert not store.ingest(trace)
    finally:
        store.close()


def test_conflict_rolls_back_new_rows_and_preserves_reviewed_memory(tmp_path):
    database = tmp_path / "memory.db"
    store = Store(database)
    original = load_trace(VALID)
    store.ingest(original)
    store.distill()
    memory = store.list_memories()[0]
    store.review(memory["id"], "approved")
    new = load_trace(ROOT / "examples/traces/environment.json")
    conflict = copy.deepcopy(original)
    conflict["events"][0]["text"] = "Conflicting input"
    with pytest.raises(ValueError, match="Conflicting"):
        store.ingest_batch([new, conflict])
    store.close()
    reopened = Store(database)
    try:
        assert reopened.db.execute("SELECT id FROM traces").fetchall()[0][0] == original["id"]
        assert reopened.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 1
        assert reopened.search("storefront", "generated client")[0]["id"] == memory["id"]
        assert reopened.ingest_batch([new, new, original]) == 1
    finally:
        reopened.close()


@pytest.mark.parametrize("failure", ["schema", "syntax", "missing"])
def test_cli_batch_load_errors_do_not_persist_earlier_files(tmp_path, failure):
    invalid = tmp_path / "invalid.json"
    if failure == "schema":
        invalid.write_text('{"schema_version": 99}')
    elif failure == "syntax":
        invalid.write_text('{"unfinished":')
    database = tmp_path / "memory.db"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "recall_lab.cli",
            "--db",
            str(database),
            "ingest",
            str(VALID),
            str(invalid),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    store = Store(database)
    try:
        assert store.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0
    finally:
        store.close()
