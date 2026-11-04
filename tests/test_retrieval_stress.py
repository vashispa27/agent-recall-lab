import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "retrieval_stress", Path(__file__).resolve().parents[1] / "experiments/retrieval_stress.py"
)
stress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stress)


def test_stress_retains_failures_and_review_boundaries():
    result = stress.run()
    assert result == stress.run()
    assert result["execution_outcomes"] is None
    assert result["live_model_outcomes"] is None
    assert len(result["cases"]) == 18
    for context in (False, True):
        cases = {
            row["case"]: row for row in result["cases"] if row["include_applicability"] == context
        }
        assert cases["literal"]["top1_correct"]
        assert not cases["paraphrase"]["top1_correct"]
        assert cases["duplicate"]["duplicate_returned"]
        assert not cases["distractor"]["top1_correct"]
        assert cases["stale-active"]["stale_returned"]
        assert not cases["stale-retired"]["stale_returned"]
        assert cases["stale-retired"]["top1_correct"]
        assert not cases["harmful-proposed"]["harmful_returned"]
        assert cases["harmful-approved"]["harmful_returned"]
        assert cases["wrong-project"]["ranked_labels"] == []
