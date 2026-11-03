"""Controlled recall hooks; retrieved text never becomes an executable action."""

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from recall_lab.core import Store


@dataclass(frozen=True)
class Action:
    """Caller-authored action identifier and retrieval context, not shell text."""

    name: str
    context: str


def run_loop(
    store: Store,
    project: str,
    task: str,
    actions: Sequence[Action],
    policy: Callable[[Action, list[dict]], bool],
    perform: Callable[[Action], object],
    mode: Literal["disabled", "task_start", "pre_command"] = "pre_command",
) -> list[dict]:
    """Recall before policy/dispatch; policy must explicitly allow each action.

    The caller owns both callbacks. Memory is untrusted advisory evidence. Task-start
    hits are reused in task_start mode; pre_command mode refreshes them for each action.
    Exceptions propagate and stop subsequent dispatch. The returned audit is in order.
    """
    if not project.strip() or not task.strip():
        raise ValueError("Project and task are required")
    if mode not in {"disabled", "task_start", "pre_command"}:
        raise ValueError("Unknown recall mode")
    audit = []

    def recall(phase: str, query: str) -> list[dict]:
        hits = store.search(project, query)
        audit.append(
            {
                "event": "recall",
                "phase": phase,
                "project": project,
                "query": query,
                "memory_ids": [hit["id"] for hit in hits],
            }
        )
        return hits

    initial = recall("task_start", task) if mode != "disabled" else []
    for action in actions:
        hits = recall("pre_command", action.context) if mode == "pre_command" else initial
        # Give policy a fresh result so it cannot corrupt hits used by a later action.
        allowed = policy(action, copy.deepcopy(hits))
        if type(allowed) is not bool:
            raise TypeError("Policy must return a boolean")
        audit.append({"event": "decision", "action": action.name, "allowed": allowed})
        if allowed:
            result = perform(action)
            audit.append({"event": "performed", "action": action.name, "result": result})
    return audit
