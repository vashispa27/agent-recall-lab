from pathlib import Path

import pytest

from recall_lab.core import Store, load_trace

SOURCE = Path(__file__).resolve().parents[1] / "examples/traces/generated-client.json"


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "memory.db")
    store.ingest(load_trace(SOURCE))
    store.distill()
    memory = store.list_memories()[0]
    store.review(memory["id"], "approved")
    yield store, memory
    store.close()


def test_replacement_requires_review_and_preserves_source(setup):
    store, old = setup
    new = store.revise(old["id"], old["project"], "Generate revised client", "Integration tests")
    assert store.search(old["project"], "client")[0]["id"] == old["id"]
    inspection = store.inspect_memory(new, old["project"])
    assert inspection["revision"]["replaces"] == old["id"]
    assert len(inspection["source_events"]) == 3
    assert inspection["extraction"] is None  # Reviewer text is not provider output.
    store.review(new, "approved")
    assert [m["id"] for m in store.search(old["project"], "client")] == [new]
    assert store.search("other-project", "client") == []
    assert store.inspect_memory(old["id"], old["project"])["memory"]["state"] == "rejected"
    assert store.distill() == 0


def test_rejected_revision_and_competing_replacements(setup):
    store, old = setup
    rejected = store.revise(old["id"], old["project"], "Bad revision", "Never")
    store.review(rejected, "rejected")
    assert store.list_memories("approved")[0]["id"] == old["id"]
    first = store.revise(old["id"], old["project"], "Client one", "Tests")
    second = store.revise(old["id"], old["project"], "Client two", "Tests")
    store.review(first, "approved")
    with pytest.raises(ValueError, match="no longer active"):
        store.review(second, "approved")
    assert store.inspect_memory(second, old["project"])["memory"]["state"] == "candidate"
    assert store.list_memories("approved")[0]["id"] == first
    with pytest.raises(ValueError):
        store.review(first, "approved")
    assert store.list_memories("approved")[0]["id"] == first


def test_revision_validation_and_redaction(setup):
    store, old = setup
    with pytest.raises(ValueError):
        store.revise(old["id"], "wrong", "text", "context")
    with pytest.raises(ValueError):
        store.revise(old["id"], old["project"], " ", "context")
    new = store.revise(old["id"], old["project"], "token=secret", "password=secret")
    shown = store.inspect_memory(new, old["project"])
    assert shown["memory"]["body"] == "token=[REDACTED]"
    assert shown["revision"]["applicability"] == "password=[REDACTED]"
