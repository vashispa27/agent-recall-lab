"""End-to-end execution outcomes, including review and project negative controls."""

import runpy
from pathlib import Path


def test_disposable_execution_comparison():
    experiment = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "experiments/local_execution.py")
    )
    result = experiment["run"]()
    assert len(result["cases"]) == 12
    for case in result["cases"]:
        expected = (
            case["reviewed"] and case["project"] == "storefront" and case["mode"] == "pre_command"
        )
        assert case["passed"] is expected
        assert [c["program"] for c in case["commands"]] == (
            ["generate", "check"] if expected else ["check"]
        )
        assert all(c["stderr"] == "" for c in case["commands"])
        assert case["commands"][-1]["stdout"] == (
            "client ready\n" if expected else "generated client missing\n"
        )
