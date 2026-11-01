"""Canonical synthetic traces and a durable, review-gated memory store.

Capture data is untrusted evidence. It is never executed by this module.
"""

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ACTIONS = {"prompt", "command", "correction", "response"}


def redact(text: str) -> str:
    return re.sub(r"(?i)(api[_-]?key|token|password)=([^\s]+)", r"\1=[REDACTED]", text)


def load_trace(path: Path) -> dict:
    trace = json.loads(path.read_text())
    for key in ("id", "project", "harness"):
        if not isinstance(trace.get(key), str) or not trace[key].strip():
            raise ValueError(f"Missing trace field: {key}")
    events = trace.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("Trace requires events")
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            raise TypeError("Event must be an object")
        if not isinstance(event.get("id"), str) or event["id"] in seen:
            raise ValueError("Event IDs must be unique strings")
        seen.add(event["id"])
        if event.get("action") not in ACTIONS or not isinstance(event.get("text"), str):
            raise ValueError("Invalid event action or text")
        if event["action"] == "command" and type(event.get("exit_code")) is not int:
            raise ValueError("Command needs an integer exit_code")
        event["text"] = redact(event["text"])
    return trace


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, project TEXT NOT NULL,
                body TEXT NOT NULL, evidence TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('candidate', 'approved', 'rejected'))
            );
        """)

    def close(self):
        self.db.close()

    def ingest(self, trace: dict) -> bool:
        payload = json.dumps(trace, sort_keys=True)
        old = self.db.execute("SELECT payload FROM traces WHERE id=?", (trace["id"],)).fetchone()
        if old:
            if old["payload"] != payload:
                raise ValueError(f"Conflicting content for trace {trace['id']}")
            return False
        with self.db:
            self.db.execute(
                "INSERT INTO traces VALUES (?, ?, ?)", (trace["id"], trace["project"], payload)
            )
        return True

    def distill(self) -> int:
        """Rule baseline: retain an explicit correction between failure and success.

        This is not LLM extraction or an endorsement of the correction's content.
        Human review is mandatory, including for malicious-looking corrections.
        """
        created = 0
        for row in self.db.execute("SELECT payload FROM traces ORDER BY id").fetchall():
            trace = json.loads(row["payload"])
            events = trace["events"]
            for i, event in enumerate(events):
                if event["action"] != "correction":
                    continue
                failures = [
                    e for e in events[:i] if e["action"] == "command" and e["exit_code"] != 0
                ]
                successes = [
                    e for e in events[i + 1 :] if e["action"] == "command" and e["exit_code"] == 0
                ]
                if not failures or not successes:
                    continue
                identity = f"{trace['id']}:{event['id']}"
                memory_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
                evidence = json.dumps([failures[-1]["id"], event["id"], successes[0]["id"]])
                with self.db:
                    result = self.db.execute(
                        "INSERT OR IGNORE INTO memories VALUES (?, ?, ?, ?, ?, 'candidate')",
                        (memory_id, trace["id"], trace["project"], event["text"], evidence),
                    )
                created += result.rowcount
        return created

    def review(self, memory_id: str, decision: str):
        if decision not in {"approved", "rejected"}:
            raise ValueError("Review decision must be approved or rejected")
        with self.db:
            result = self.db.execute(
                "UPDATE memories SET state=? WHERE id=? AND state='candidate'",
                (decision, memory_id),
            )
            if result.rowcount != 1:
                raise ValueError("Memory is absent or already reviewed")

    def list_memories(self, state: str = "candidate") -> list[dict]:
        return [
            dict(row)
            for row in self.db.execute("SELECT * FROM memories WHERE state=? ORDER BY id", (state,))
        ]

    def search(self, project: str, query: str, limit: int = 5) -> list[dict]:
        if not project.strip() or limit < 1:
            raise ValueError("A project and positive limit are required")
        terms = tokenize(query)
        if not terms:
            return []
        ranked = []
        for row in self.db.execute(
            "SELECT * FROM memories WHERE project=? AND state='approved'", (project,)
        ):
            item = dict(row)
            score = len(terms & tokenize(item["body"])) / len(terms)
            if score:
                item["score"] = score
                item["evidence"] = json.loads(item["evidence"])
                ranked.append(item)
        return sorted(ranked, key=lambda m: (-m["score"], m["id"]))[:limit]
