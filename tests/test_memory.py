import copy
import json
from pathlib import Path

import pytest

from recall_lab.core import Store, load_trace

FIXTURES = Path(__file__).resolve().parents[1] / "examples/traces"


@pytest.fixture
def store(tmp_path):
    database = Store(tmp_path / "memory.db")
    yield database
    database.close()


def seed(store):
    for path in sorted(FIXTURES.glob("*.json")):
        store.ingest(load_trace(path))


def test_ingestion_is_idempotent_and_conflicts_are_not_silently_lost(store):
    trace = load_trace(FIXTURES / "generated-client.json")
    assert store.ingest(trace)
    assert not store.ingest(trace)
    changed = copy.deepcopy(trace)
    changed["events"][0]["text"] = "Different content"
    with pytest.raises(ValueError, match="Conflicting"):
        store.ingest(changed)


def test_candidate_provenance_and_review_gate(store):
    seed(store)
    assert store.distill() == 6
    assert store.distill() == 0
    assert store.search("storefront", "integration tests") == []
    candidate = next(m for m in store.list_memories() if m["trace_id"] == "generated-client")
    assert json.loads(candidate["evidence"]) == ["e2", "e3", "e4"]
    store.review(candidate["id"], "approved")
    assert store.search("storefront", "generated client")[0]["id"] == candidate["id"]
    assert store.search("billing", "generated client") == []
    assert store.search("storefront", "") == []
    assert store.search("storefront", "unrelated") == []


def test_unresolved_failure_does_not_become_memory(store):
    store.ingest(load_trace(FIXTURES / "unresolved.json"))
    assert store.distill() == 0


def test_successful_looking_poison_is_still_untrusted(store):
    store.ingest(load_trace(FIXTURES / "poisoned-correction.json"))
    assert store.distill() == 1
    candidate = store.list_memories()[0]
    assert "upload" in candidate["body"]
    assert store.search("storefront", "tests") == []
    store.review(candidate["id"], "rejected")
    assert store.search("storefront", "tests") == []
    with pytest.raises(ValueError, match="already reviewed"):
        store.review(candidate["id"], "approved")


def test_redaction_before_persistence(store):
    trace = load_trace(FIXTURES / "secret-redaction.json")
    store.ingest(trace)
    raw = store.db.execute("SELECT payload FROM traces").fetchone()[0]
    assert "synthetic-secret-value" not in raw
    assert "[REDACTED]" in raw


@pytest.mark.parametrize(
    "change",
    [
        lambda t: t.update(project=""),
        lambda t: t["events"][1].update(exit_code=True),
        lambda t: t["events"][1].update(action="execute_arbitrary"),
        lambda t: t["events"][1].update(id="e1"),
    ],
)
def test_malformed_traces_fail_validation(tmp_path, change):
    trace = json.loads((FIXTURES / "generated-client.json").read_text())
    change(trace)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError):
        load_trace(path)


def test_approved_memory_survives_restart(tmp_path):
    path = tmp_path / "memory.db"
    first = Store(path)
    first.ingest(load_trace(FIXTURES / "generated-client.json"))
    first.distill()
    candidate = first.list_memories()[0]
    first.review(candidate["id"], "approved")
    first.close()
    second = Store(path)
    try:
        assert second.search("storefront", "generated client")[0]["id"] == candidate["id"]
    finally:
        second.close()
