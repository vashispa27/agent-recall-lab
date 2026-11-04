"""Protect the fixed evaluation boundary and repeatability."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "frozen_evaluation", Path(__file__).resolve().parents[1] / "experiments/frozen_evaluation.py"
)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def test_changed_input_is_rejected_before_evaluation(tmp_path):
    for path in evaluation.DATA.glob("*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    with (tmp_path / "tasks.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="Frozen evaluation input changed: tasks.json"):
        evaluation.load_dataset(tmp_path)


def test_evaluation_is_repeatable_and_review_project_bound():
    first = evaluation.run()
    assert first == evaluation.run()
    for row in first["cases"]:
        assert "unsafe-shortcut" not in row["ranked_traces"]
        if row["category"] == "isolation":
            assert row["ranked_traces"] == []
