"""Opt-in import of a single, finished Codex exec JSONL export."""

import hashlib
import json
import os
import stat
from pathlib import Path

from recall_lab.adapters import adapt_trace
from recall_lab.core import parse_json, validate_trace

MAX_BYTES = 1024 * 1024
MAX_RECORDS = 2000


def load_codex_export(path: Path, project: str, corrections: list[str], synthetic: bool) -> dict:
    # Open without following the final symlink or waiting on a pipe.
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("Capture requires a regular file")
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or not raw.endswith(b"\n"):
        raise ValueError("Capture exceeds the byte limit or lacks a final newline")
    lines = raw.split(b"\n")[:-1]
    if not 4 <= len(lines) <= MAX_RECORDS:
        raise ValueError("Capture record count is out of bounds")
    records = [parse_json(line.decode("utf-8")) for line in lines]
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Capture requires JSON objects")
    thread, start, *items, end = records
    thread_id = thread.get("thread_id")
    if (
        thread.get("type") != "thread.started"
        or not isinstance(thread_id, str)
        or not thread_id.strip()
        or start != {"type": "turn.started"}
        or end.get("type") != "turn.completed"
    ):
        raise ValueError("Capture requires one successful, complete turn")
    completed = []
    for record in items:
        kind = record.get("type")
        if kind == "item.completed":
            completed.append(record)
        elif kind not in ("item.started", "item.updated"):
            raise ValueError("Unsupported capture record")
    identity = hashlib.sha256(json.dumps([project, thread_id]).encode()).hexdigest()
    trace = adapt_trace(
        {
            "synthetic": True,
            "id": f"codex-exec-{identity}",
            "project": project,
            "correction_ids": corrections,
            "records": completed,
        },
        "codex",
    )
    trace["synthetic"] = synthetic
    trace["provenance"] = {
        "adapter": "codex-exec-jsonl-v1",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }
    return validate_trace(trace)
