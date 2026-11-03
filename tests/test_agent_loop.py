import pytest

from recall_lab.agent_loop import Action, run_loop


class SearchSpy:
    def __init__(self):
        self.calls = []

    def search(self, project, query):
        self.calls.append((project, query))
        return [{"id": "approved", "lesson": "untrusted text"}]


@pytest.mark.parametrize("mode,count", [("disabled", 0), ("task_start", 1), ("pre_command", 3)])
def test_recall_precedes_policy_and_dispatch(mode, count):
    store = SearchSpy()
    seen = []

    def policy(action, hits):
        seen.append((action.name, len(store.calls)))
        return action.name == "allowed"

    dispatched = []
    audit = run_loop(
        store,
        "project",
        "task",
        [Action("blocked", "first"), Action("allowed", "second")],
        policy,
        lambda action: dispatched.append(action.name),
        mode,
    )
    assert len(store.calls) == count
    assert all(project == "project" for project, _ in store.calls)
    assert seen == [("blocked", min(count, 2)), ("allowed", count)]
    assert dispatched == ["allowed"]
    assert [e["event"] for e in audit if e["event"] != "recall"] == [
        "decision",
        "decision",
        "performed",
    ]


def test_policy_mutation_cannot_change_later_context():
    observed = []

    def policy(action, hits):
        observed.append(hits[0]["lesson"])
        hits[0]["lesson"] = "mutated"
        return False

    run_loop(
        SearchSpy(),
        "p",
        "t",
        [Action("a", "a")] * 2,
        policy,
        lambda _: pytest.fail("blocked action dispatched"),
        "task_start",
    )
    assert observed == ["untrusted text"] * 2


def test_exception_stops_dispatch():
    def fail(action):
        raise RuntimeError("callback failed")

    store = SearchSpy()
    with pytest.raises(RuntimeError, match="callback failed"):
        run_loop(store, "p", "t", [Action("a", "a")] * 2, lambda *_: True, fail)
    assert len(store.calls) == 2


def test_invalid_policy_is_not_permission():
    with pytest.raises(TypeError, match="boolean"):
        run_loop(
            SearchSpy(),
            "p",
            "t",
            [Action("a", "a")],
            lambda *_: "yes",
            lambda _: pytest.fail("dispatched"),
        )


@pytest.mark.parametrize(
    "project,task,mode", [("", "t", "disabled"), ("p", "", "disabled"), ("p", "t", "unknown")]
)
def test_invalid_configuration(project, task, mode):
    with pytest.raises(ValueError):
        run_loop(SearchSpy(), project, task, [], lambda *_: True, lambda _: None, mode)


def test_real_store_review_and_project_boundaries(tmp_path):
    from pathlib import Path

    from recall_lab.core import Store, load_trace

    store = Store(tmp_path / "memory.db")
    try:
        fixture = Path(__file__).resolve().parents[1] / "examples/traces/generated-client.json"
        store.ingest(load_trace(fixture))
        store.distill()
        action = Action("check", "integration tests generated client")

        def audit(project):
            return run_loop(
                store,
                project,
                "generic task",
                [action],
                lambda _, hits: bool(hits),
                lambda _: "callback",
            )

        assert not any(e["event"] == "performed" for e in audit("storefront"))
        store.review(store.list_memories()[0]["id"], "approved")
        assert any(e["event"] == "performed" for e in audit("storefront"))
        assert not any(e["event"] == "performed" for e in audit("other"))
    finally:
        store.close()
