"""Review and project boundaries survive opt-in contextual retrieval."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "applicability", Path(__file__).resolve().parents[1] / "experiments/applicability_comparison.py"
)
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)


def test_context_ablation_preserves_boundaries_and_negative_outcomes():
    result = comparison.run()
    assert result == comparison.run()
    assert result["proposed_context_excluded"]
    rows = {(r["case"], r["mode"]): r for r in result["cases"]}
    for mode in ("body", "body+applicability"):
        assert rows["wrong-project", mode]["ranked_ids"] == []
    assert not rows["task-context", "body"]["correct"]
    assert rows["task-context", "body+applicability"]["correct"]
    assert rows["command-context", "body+applicability"]["correct"]
    assert not rows["negated-context", "body+applicability"]["correct"]
