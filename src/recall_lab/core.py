"""Canonical traces and a durable, review-gated memory store.

Capture data is untrusted evidence. It is never executed by this module.
"""

import copy
import hashlib
import json
import re
import sqlite3
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

TRACE_SCHEMA = json.loads(files("recall_lab").joinpath("schemas/trace.schema.json").read_text())
TRACE_VALIDATOR = Draft202012Validator(TRACE_SCHEMA)


def redact(text: str) -> str:
    return re.sub(r"(?i)(api[_-]?key|token|password)=([^\s]+)", r"\1=[REDACTED]", text)


def validate_trace(trace: object) -> dict:
    """Validate and copy untrusted input; never persist unknown fields or raw text.

    The schema describes structural rules. Event identity uniqueness is an additional
    semantic constraint, required to keep evidence links unambiguous.
    """
    error = next(TRACE_VALIDATOR.iter_errors(trace), None)
    if error is not None:
        location = ".".join(map(str, error.absolute_path)) or "trace"
        # Avoid echoing untrusted values (which can contain credentials).
        raise ValueError(f"Invalid trace at {location}: schema rule {error.validator}")
    normalized = copy.deepcopy(trace)
    seen = set()
    for event in normalized["events"]:
        if event["id"] in seen:
            raise ValueError("Event IDs must be unique strings")
        seen.add(event["id"])
        event["text"] = redact(event["text"])
    return normalized


def parse_json(text: str) -> object:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=unique_keys)


def read_json(path: Path) -> object:
    return parse_json(path.read_text())


def load_trace(path: Path) -> dict:
    return validate_trace(read_json(path))


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
            CREATE TABLE IF NOT EXISTS memory_revisions (
                memory_id TEXT PRIMARY KEY, replaces TEXT NOT NULL,
                applicability TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_extractions (
                memory_id TEXT PRIMARY KEY, provider TEXT NOT NULL,
                source_sha256 TEXT NOT NULL
            );
        """)

    def close(self):
        self.db.close()

    def ingest(self, trace: dict) -> bool:
        return bool(self.ingest_batch([trace]))

    def ingest_batch(self, traces) -> int:
        """Import all inputs in one transaction, including lazily loaded files.

        A malformed input or conflicting ID rolls back every insert in the batch.
        Existing identical redacted traces are idempotent duplicates.
        """
        inserted = 0
        with self.db:
            for trace in traces:
                trace = validate_trace(trace)
                payload = json.dumps(trace, sort_keys=True)
                old = self.db.execute(
                    "SELECT payload FROM traces WHERE id=?", (trace["id"],)
                ).fetchone()
                if old:
                    if old["payload"] != payload:
                        raise ValueError("Conflicting content for trace ID")
                    continue
                self.db.execute(
                    "INSERT INTO traces VALUES (?, ?, ?)", (trace["id"], trace["project"], payload)
                )
                inserted += 1
        return inserted

    def distill(self, provider=None) -> int:
        """Validate untrusted proposals and persist a whole extraction batch atomically.

        Existing review decisions and candidate identities are never overwritten.
        Ordering establishes evidence links, not causality or correction safety.
        """
        from recall_lab.extraction import (
            CorrectionRuleExtractor,
            validate_proposal,
            validate_provider,
        )

        if provider is None:
            provider = CorrectionRuleExtractor()
        provider_id = validate_provider(provider)
        created = 0
        with self.db:
            for row in self.db.execute("SELECT payload FROM traces ORDER BY id").fetchall():
                trace = validate_trace(json.loads(row["payload"]))
                digest = hashlib.sha256(
                    json.dumps(trace, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                for raw in provider.extract(copy.deepcopy(trace)):
                    proposal = validate_proposal(raw, trace)
                    identity = f"{trace['id']}:{proposal.evidence[1]}"
                    memory_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
                    evidence = json.dumps(proposal.evidence)
                    old = self.db.execute(
                        "SELECT body, evidence FROM memories WHERE id=?", (memory_id,)
                    ).fetchone()
                    if old:
                        if old["body"] != proposal.body or old["evidence"] != evidence:
                            raise ValueError("Conflicting candidate for source correction")
                        continue
                    self.db.execute(
                        "INSERT INTO memories VALUES (?, ?, ?, ?, ?, 'candidate')",
                        (memory_id, trace["id"], trace["project"], proposal.body, evidence),
                    )
                    self.db.execute(
                        "INSERT INTO memory_extractions VALUES (?, ?, ?)",
                        (memory_id, provider_id, digest),
                    )
                    created += 1
        return created

    def inspect_memory(self, memory_id: str, project: str) -> dict:
        """Return redacted source events and extraction metadata within a project."""
        if not isinstance(project, str) or not project.strip():
            raise ValueError("A project is required")
        row = self.db.execute(
            "SELECT * FROM memories WHERE id=? AND project=?", (memory_id, project)
        ).fetchone()
        if row is None:
            raise ValueError("Memory not found in project")
        memory = dict(row)
        memory["evidence"] = json.loads(memory["evidence"])
        trace = json.loads(
            self.db.execute(
                "SELECT payload FROM traces WHERE id=?", (memory["trace_id"],)
            ).fetchone()[0]
        )
        events = {e["id"]: e for e in trace["events"]}
        metadata = self.db.execute(
            "SELECT provider, source_sha256 FROM memory_extractions WHERE memory_id=?", (memory_id,)
        ).fetchone()
        return {
            "memory": memory,
            "source_events": [events[x] for x in memory["evidence"]],
            "trace_provenance": trace.get("provenance"),
            "extraction": dict(metadata) if metadata else None,
            "revision": self._revision(memory_id),
        }

    def _revision(self, memory_id: str):
        row = self.db.execute(
            "SELECT replaces, applicability FROM memory_revisions WHERE memory_id=?",
            (memory_id,),
        ).fetchone()
        return dict(row) if row else None

    def revise(self, memory_id: str, project: str, body: str, applicability: str) -> str:
        """Propose a replacement without changing the approved source or its evidence.

        Applicability is reviewer-readable context, not an enforced command policy.
        Approval atomically retires the old lesson; rejected revisions leave it active.
        """
        if not all(isinstance(x, str) and x.strip() for x in (body, applicability)):
            raise ValueError("Body and applicability must be nonempty text")
        source = self.inspect_memory(memory_id, project)["memory"]
        if source["state"] != "approved":
            raise ValueError("Only an active approved memory can be revised")
        body, applicability = redact(body.strip()), redact(applicability.strip())
        replacement = hashlib.sha256(
            json.dumps([memory_id, body, applicability]).encode()
        ).hexdigest()[:16]
        with self.db:
            self.db.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, 'candidate')",
                (replacement, source["trace_id"], project, body, json.dumps(source["evidence"])),
            )
            self.db.execute(
                "INSERT INTO memory_revisions VALUES (?, ?, ?)",
                (replacement, memory_id, applicability),
            )
        return replacement

    def review(self, memory_id: str, decision: str):
        if decision not in {"approved", "rejected"}:
            raise ValueError("Review decision must be approved or rejected")
        with self.db:
            revision = self.db.execute(
                "SELECT replaces FROM memory_revisions WHERE memory_id=?", (memory_id,)
            ).fetchone()
            if revision and decision == "approved":
                retired = self.db.execute(
                    "UPDATE memories SET state='rejected' WHERE id=? AND state='approved'",
                    (revision["replaces"],),
                )
                if retired.rowcount != 1:
                    raise ValueError("Replacement source is no longer active")
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

    def search(
        self, project: str, query: str, limit: int = 5, *, include_applicability: bool = False
    ) -> list[dict]:
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
            revision = self._revision(item["id"])
            text = item["body"]
            if include_applicability and revision:
                text += " " + revision["applicability"]
            score = len(terms & tokenize(text)) / len(terms)
            if score:
                if revision:
                    item["revision"] = revision
                item["score"] = score
                item["evidence"] = json.loads(item["evidence"])
                ranked.append(item)
        return sorted(ranked, key=lambda m: (-m["score"], m["id"]))[:limit]
