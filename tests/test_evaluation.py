
from collections import Counter

import evaluation.runner as runner


def test_dataset_contains_24_balanced_examples():
    dataset = runner.load_dataset(
        runner.PROJECT_ROOT / "evaluation" / "dataset.json"
    )

    labels = Counter(
        item["expected_relation"] for item in dataset
    )

    assert len(dataset) == 24
    assert labels == {
        "supports": 8,
        "contradicts": 8,
        "irrelevant": 8,
    }


def test_classify_prediction_returns_supports():
    result = {
        "evidence": [
            {
                "article_index": 1,
                "relation": "supports",
            }
        ]
    }

    prediction, status = runner.classify_prediction(result)

    assert prediction == "supports"
    assert status == "classified"


def test_classify_prediction_returns_abstention_for_empty_evidence():
    prediction, status = runner.classify_prediction(
        {"evidence": []}
    )

    assert prediction is None
    assert status == "abstained"


def test_classify_prediction_rejects_conflicting_relations():
    result = {
        "evidence": [
            {
                "article_index": 1,
                "relation": "supports",
            },
            {
                "article_index": 1,
                "relation": "contradicts",
            },
        ]
    }

    prediction, status = runner.classify_prediction(result)

    assert prediction is None
    assert status == "ambiguous_prediction"


def test_classify_prediction_ignores_invalid_article_index():
    result = {
        "evidence": [
            {
                "article_index": 2,
                "relation": "supports",
            }
        ]
    }

    prediction, status = runner.classify_prediction(result)

    assert prediction is None
    assert status == "abstained"


def test_retryable_errors_are_identified():
    assert runner.is_retryable_error(
        RuntimeError("503 UNAVAILABLE")
    )

    assert runner.is_retryable_error(
        RuntimeError("429 RESOURCE_EXHAUSTED")
    )


def test_non_retryable_error_is_identified():
    assert not runner.is_retryable_error(
        RuntimeError("400 INVALID_ARGUMENT")
    )


def test_evaluation_retries_temporary_provider_error(monkeypatch):
    calls = {"count": 0}

    def fake_analyze_claim(claim, articles):
        calls["count"] += 1

        if calls["count"] == 1:
            raise RuntimeError("503 UNAVAILABLE")

        return {
            "evidence": [
                {
                    "article_index": 1,
                    "relation": "supports",
                }
            ]
        }

    monkeypatch.setattr(
        runner,
        "analyze_claim",
        fake_analyze_claim,
    )

    dataset = [
        {
            "id": "SUP_TEST",
            "category": "direct_support",
            "claim": "Test claim",
            "articles": [{"title": "Test article"}],
            "expected_relation": "supports",
        }
    ]

    report = runner.run_evaluation(
        dataset,
        delay=0,
        max_retries=2,
        retry_delay=0,
    )

    prediction = report["predictions"][0]
    metrics = report["results"]

    assert calls["count"] == 2
    assert prediction["attempts"] == 2
    assert prediction["predicted"] == "supports"
    assert prediction["correct"] is True
    assert metrics["provider_errors"] == 0
    assert metrics["request_success_rate"] == 1.0


def test_permanent_provider_error_is_not_counted_as_abstention(
    monkeypatch,
):
    def fake_analyze_claim(claim, articles):
        raise RuntimeError("400 INVALID_ARGUMENT")

    monkeypatch.setattr(
        runner,
        "analyze_claim",
        fake_analyze_claim,
    )

    dataset = [
        {
            "id": "SUP_ERROR",
            "category": "direct_support",
            "claim": "Test claim",
            "articles": [{"title": "Test article"}],
            "expected_relation": "supports",
        }
    ]

    report = runner.run_evaluation(
        dataset,
        delay=0,
        max_retries=2,
        retry_delay=0,
    )

    metrics = report["results"]
    prediction = report["predictions"][0]

    assert prediction["status"] == "provider_error"
    assert prediction["attempts"] == 1
    assert metrics["provider_errors"] == 1
    assert metrics["abstentions"] == 0
    assert metrics["evaluated_samples"] == 0
    assert metrics["request_success_rate"] == 0.0
