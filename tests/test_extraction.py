import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from recall_lab.core import Store, load_trace
from recall_lab.extraction import CandidateProposal, CorrectionRuleExtractor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "memory.db")
    store.ingest(load_trace(ROOT / "examples/traces/generated-client.json"))
    yield store
    store.close()


def test_provider_provenance_inspection_and_restart(store):
    assert store.distill(CorrectionRuleExtractor()) == 1
    memory = store.list_memories()[0]
    inspection = store.inspect_memory(memory["id"], "storefront")
    assert [e["id"] for e in inspection["source_events"]] == ["e2", "e3", "e4"]
    assert inspection["extraction"]["provider"] == "explicit-correction-v1"
    trace = load_trace(ROOT / "examples/traces/generated-client.json")
    expected = hashlib.sha256(json.dumps(trace, sort_keys=True, separators=(",", ":")).encode())
    assert inspection["extraction"]["source_sha256"] == expected.hexdigest()
    store.review(memory["id"], "approved")
    assert store.distill() == 0
    assert store.inspect_memory(memory["id"], "storefront")["memory"]["state"] == "approved"
    with pytest.raises(ValueError, match="not found"):
        store.inspect_memory(memory["id"], "other-project")
    db_path = store.db.execute("PRAGMA database_list").fetchone()[2]
    reopened = Store(Path(db_path))
    try:
        assert (
            reopened.inspect_memory(memory["id"], "storefront")["extraction"]
            == inspection["extraction"]
        )
    finally:
        reopened.close()


class Provider:
    provider_id = "test-provider-v1"

    def __init__(self, proposals):
        self.proposals = proposals

    def extract(self, trace):
        return iter(self.proposals)


@pytest.mark.parametrize(
    "proposal",
    [
        CandidateProposal("", ("e2", "e3", "e4")),
        CandidateProposal("bad", ("e2", "other-trace-event", "e4")),
        CandidateProposal("bad", ("e4", "e3", "e2")),
        CandidateProposal("bad", ("e1", "e3", "e4")),
        CandidateProposal("bad", ("e2", "e2", "e4")),
        CandidateProposal("bad", ("e2", "e3", "e3")),
        {"body": "bad", "evidence": ["e2", "e3", "e4"], "state": "approved"},
    ],
)
def test_invalid_proposal_rolls_back_whole_batch(store, proposal):
    good = CandidateProposal("valid", ("e2", "e3", "e4"))
    with pytest.raises(ValueError):
        store.distill(Provider([good, proposal]))
    assert store.list_memories() == []
    assert store.db.execute("SELECT COUNT(*) FROM memory_extractions").fetchone()[0] == 0


def test_provider_cannot_change_source_project_or_evidence(store):
    class MutatingProvider:
        provider_id = "mutating-test"

        def extract(self, trace):
            trace["project"] = "attacker-project"
            trace["events"][1]["exit_code"] = 0
            yield CandidateProposal("token=synthetic-proposal-secret", ("e2", "e3", "e4"))

    assert store.distill(MutatingProvider()) == 1
    memory = store.list_memories()[0]
    assert memory["project"] == "storefront"
    assert memory["body"] == "token=[REDACTED]"
    assert store.inspect_memory(memory["id"], "storefront")["source_events"][0]["exit_code"] == 1
    assert store.search("storefront", "token") == []


def test_provider_failure_rolls_back_and_preserves_review(store):
    store.distill()
    memory = store.list_memories()[0]
    store.review(memory["id"], "rejected")
    store.ingest(load_trace(ROOT / "examples/traces/environment.json"))

    class FailingProvider(CorrectionRuleExtractor):
        def extract(self, trace):
            yield from super().extract(trace)
            raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="unavailable"):
        store.distill(FailingProvider())
    assert store.list_memories() == []
    assert store.list_memories("rejected")[0]["id"] == memory["id"]
    assert store.db.execute("SELECT COUNT(*) FROM memory_extractions").fetchone()[0] == 1


def test_conflicting_provider_does_not_overwrite_approved_memory(store):
    store.distill()
    memory = store.list_memories()[0]
    store.review(memory["id"], "approved")
    with pytest.raises(ValueError, match="Conflicting"):
        store.distill(Provider([CandidateProposal("replacement", ("e2", "e3", "e4"))]))
    assert store.search("storefront", "generated client")[0]["body"] == memory["body"]


def test_invalid_provider_identity_is_rejected(store):
    provider = Provider([])
    provider.provider_id = "token=do-not-echo"
    with pytest.raises(ValueError, match="identity") as error:
        store.distill(provider)
    assert "do-not-echo" not in str(error.value)


def test_legacy_rows_do_not_gain_fabricated_extraction_metadata(store):
    store.distill()
    memory = store.list_memories()[0]
    store.db.execute("DELETE FROM memory_extractions")
    store.db.commit()
    assert store.distill() == 0
    assert store.inspect_memory(memory["id"], "storefront")["extraction"] is None


def test_cli_show_requires_matching_project(store):
    store.distill()
    memory = store.list_memories()[0]
    database = store.db.execute("PRAGMA database_list").fetchone()[2]
    command = [
        sys.executable,
        "-m",
        "recall_lab.cli",
        "--db",
        database,
        "show",
        memory["id"],
        "--project",
    ]
    result = subprocess.run([*command, "storefront"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["source_events"][1]["action"] == "correction"
    denied = subprocess.run([*command, "other"], capture_output=True, text=True, check=False)
    assert denied.returncode != 0
    assert memory["body"] not in denied.stdout
