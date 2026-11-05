import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from recall_lab.capture import MAX_BYTES, MAX_RECORDS, load_codex_export
from recall_lab.core import Store

FIXTURE = Path(__file__).resolve().parents[1] / "examples/native/codex-exec.jsonl"


def test_capture_cli_retains_review_gate_and_source(tmp_path):
    db = tmp_path / "memory.db"
    command = [
        sys.executable,
        "-m",
        "recall_lab.cli",
        "--db",
        str(db),
        "capture",
        str(FIXTURE),
        "--project",
        "analytics",
        "--correction",
        "item2",
        "--synthetic",
    ]
    for expected in [1, 0]:
        result = subprocess.run(command, cwd=tmp_path, capture_output=True, check=True)
        assert json.loads(result.stdout) == {"inserted": expected}
    assert not (tmp_path / "sentinel").exists()

    store = Store(db)
    try:
        assert store.distill() == 1
        candidate = store.list_memories()[0]
        source = store.inspect_memory(candidate["id"], "analytics")
        assert source["trace_provenance"] == {
            "adapter": "codex-exec-jsonl-v1",
            "source_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        }
        assert json.loads(candidate["evidence"]) == ["item1", "item2", "item3"]
        assert "fixture-value" not in json.dumps(source)
        assert "[REDACTED]" in json.dumps(source)
        assert store.search("analytics", "pytest") == []
        store.review(candidate["id"], "approved")
    finally:
        store.close()

    store = Store(db)
    try:
        assert store.search("analytics", "pytest")
        assert store.search("elsewhere", "pytest") == []
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    ["truncated", "missing_end", "unsupported", "duplicate_key", "oversize", "too_many"],
)
def test_rejected_capture_is_atomic(tmp_path, case):
    path = tmp_path / "export.jsonl"
    raw = FIXTURE.read_bytes()
    variants = {
        "truncated": raw[:-2],
        "missing_end": b"\n".join(raw.splitlines()[:-1]) + b"\n",
        "unsupported": raw.replace(b"item.completed", b"unknown.record", 1),
        "duplicate_key": raw.replace(b'"thread_id":', b'"type":"ignored","thread_id":', 1),
        "oversize": b"x" * (MAX_BYTES + 1),
        "too_many": b"{}\n" * (MAX_RECORDS + 1),
    }
    path.write_bytes(variants[case])
    db = tmp_path / "memory.db"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "recall_lab.cli",
            "--db",
            str(db),
            "capture",
            str(path),
            "--project",
            "analytics",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert b"Capture rejected" in result.stderr
    assert b"fixture-value" not in result.stderr
    store = Store(db)
    try:
        assert store.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0
    finally:
        store.close()


def test_capture_explicit_annotation_and_identity(tmp_path):
    trace = load_codex_export(FIXTURE, "analytics", [], True)
    assert trace["synthetic"]
    assert not any(event["action"] == "correction" for event in trace["events"])
    # Only test the label plumbing with invented bytes.
    assert load_codex_export(FIXTURE, "analytics", [], False)["synthetic"] is False
    assert trace["id"] != load_codex_export(FIXTURE, "elsewhere", [], True)["id"]
    with pytest.raises(ValueError):
        load_codex_export(FIXTURE, "analytics", ["item1"], True)
    store = Store(tmp_path / "memory.db")
    try:
        assert store.ingest(trace)
        with pytest.raises(ValueError):
            store.ingest(load_codex_export(FIXTURE, "analytics", ["item2"], True))
        assert store.distill() == 0
    finally:
        store.close()


def test_capture_rejects_symlink_and_fifo(tmp_path):
    path = tmp_path / "symlink"
    path.symlink_to(FIXTURE)
    with pytest.raises(OSError):
        load_codex_export(path, "analytics", [], True)
    pipe = tmp_path / "pipe"
    os.mkfifo(pipe)
    with pytest.raises(ValueError, match="regular file"):
        load_codex_export(pipe, "analytics", [], True)
