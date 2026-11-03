
import argparse
import json
import sys
import time

from datetime import datetime, timezone
from pathlib import Path


# Ensure the project root is available when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ai_verifier import analyze_claim


CLASSES = ["supports", "contradicts", "irrelevant"]
PREDICTION_COLUMNS = CLASSES + ["abstain", "provider_error"]

def load_dataset(path: Path) -> list[dict]:
    """Load and validate the evaluation dataset."""

    with path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("Evaluation dataset must be a non-empty JSON list.")

    seen_ids = set()

    for index, sample in enumerate(dataset):
        required = {
            "id",
            "claim",
            "articles",
            "expected_relation",
        }

        if not isinstance(sample, dict) or not required.issubset(sample):
            raise ValueError(
                f"Dataset item {index} is missing required fields."
            )

        if sample["id"] in seen_ids:
            raise ValueError(f"Duplicate dataset ID: {sample['id']}")

        seen_ids.add(sample["id"])

        if sample["expected_relation"] not in CLASSES:
            raise ValueError(
                f"Invalid expected relation in {sample['id']}."
            )

        if not isinstance(sample["articles"], list) or not sample["articles"]:
            raise ValueError(
                f"Sample {sample['id']} must contain at least one article."
            )

    return dataset


def classify_prediction(result: dict) -> tuple[str | None, str]:
    """
    Extract the prediction for the single supplied article.

    Missing predictions and conflicting predictions are abstentions,
    not automatically irrelevant classifications.
    """

    evidence = result.get("evidence")

    if not isinstance(evidence, list):
        return None, "invalid_response"

    predictions = set()

    for item in evidence:
        if not isinstance(item, dict):
            continue

        article_index = item.get("article_index")
        relation = item.get("relation")

        if (
            isinstance(article_index, int)
            and not isinstance(article_index, bool)
            and article_index == 1
            and relation in CLASSES
        ):
            predictions.add(relation)

    if not predictions:
        return None, "abstained"

    if len(predictions) > 1:
        return None, "ambiguous_prediction"

    return predictions.pop(), "classified"


def calculate_metrics(rows: list[dict]) -> dict:
    """Calculate model metrics separately from provider failures."""

    confusion_matrix = {
        actual: {predicted: 0 for predicted in PREDICTION_COLUMNS}
        for actual in CLASSES
    }

    for row in rows:
        actual = row["expected"]
        predicted = row["predicted"]

        if row["status"] == "provider_error":
            column = "provider_error"
        elif predicted in CLASSES:
            column = predicted
        else:
            column = "abstain"

        confusion_matrix[actual][column] += 1

    evaluated_rows = [
        row for row in rows
        if row["status"] != "provider_error"
    ]

    total_samples = len(rows)
    evaluated_samples = len(evaluated_rows)

    answered = sum(
        row["predicted"] in CLASSES
        for row in evaluated_rows
    )

    correct = sum(
        row["predicted"] == row["expected"]
        for row in evaluated_rows
    )

    provider_errors = total_samples - evaluated_samples

    per_class = {}

    for label in CLASSES:
        true_positive = confusion_matrix[label][label]

        false_positive = sum(
            confusion_matrix[other][label]
            for other in CLASSES
            if other != label
        )

        false_negative = (
            sum(
                confusion_matrix[label][other]
                for other in CLASSES
                if other != label
            )
            + confusion_matrix[label]["abstain"]
        )

        support = sum(
            confusion_matrix[label][column]
            for column in CLASSES + ["abstain"]
        )

        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive else 0.0
        )

        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative else 0.0
        )

        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0.0
        )

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    macro_precision = sum(
        values["precision"] for values in per_class.values()
    ) / len(CLASSES)

    macro_recall = sum(
        values["recall"] for values in per_class.values()
    ) / len(CLASSES)

    macro_f1 = sum(
        values["f1"] for values in per_class.values()
    ) / len(CLASSES)

    return {
        "total_samples": total_samples,
        "evaluated_samples": evaluated_samples,
        "correct_predictions": correct,
        "answered_predictions": answered,
        "abstentions": evaluated_samples - answered,
        "provider_errors": provider_errors,
        "request_success_rate": round(
            evaluated_samples / total_samples, 4
        ) if total_samples else 0.0,
        "coverage": round(
            answered / evaluated_samples, 4
        ) if evaluated_samples else 0.0,
        "accuracy": round(
            correct / evaluated_samples, 4
        ) if evaluated_samples else 0.0,
        "selective_accuracy": round(
            correct / answered, 4
        ) if answered else 0.0,
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "balanced_accuracy": round(macro_recall, 4),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix,
    }

def is_retryable_error(exc: Exception) -> bool:
    """Identify temporary provider errors that may succeed on retry."""

    message = str(exc).upper()

    retryable_markers = (
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
    )

    return any(marker in message for marker in retryable_markers)


def run_evaluation(
    dataset: list[dict],
    delay: float = 1.0,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> dict:
    """Run the benchmark with retries for temporary API failures."""

    rows = []

    for index, sample in enumerate(dataset, start=1):
        print(
            f"[{index}/{len(dataset)}] Evaluating {sample['id']}...",
            flush=True,
        )

        result = None
        error = None
        attempts = 0

        for attempt in range(max_retries + 1):
            attempts = attempt + 1

            try:
                result = analyze_claim(
                    claim=sample["claim"],
                    articles=sample["articles"],
                )
                error = None
                break

            except Exception as exc:
                error = exc

                if (
                    not is_retryable_error(exc)
                    or attempt == max_retries
                ):
                    break

                wait = retry_delay * (2 ** attempt)

                print(
                    f"Temporary provider error. "
                    f"Retry {attempt + 1}/{max_retries} "
                    f"in {wait:.1f}s: {exc}",
                    flush=True,
                )

                time.sleep(wait)

        if error is not None:
            predicted = None
            status = "provider_error"

        else:
            predicted, status = classify_prediction(result)

        rows.append({
            "id": sample["id"],
            "category": sample.get("category"),
            "expected": sample["expected_relation"],
            "predicted": predicted,
            "status": status,
            "correct": predicted == sample["expected_relation"],
            "attempts": attempts,
            "error": str(error) if error else None,
        })

        if delay > 0 and index < len(dataset):
            time.sleep(delay)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": calculate_metrics(rows),
        "predictions": rows,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate VerifyAI article classification."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dataset.json",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "results" / "latest.json",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between AI requests in seconds.",
    )

    args = parser.parse_args()

    if args.delay < 0:
        parser.error("--delay cannot be negative.")

    dataset = load_dataset(args.dataset)

    print(f"\nLoaded {len(dataset)} evaluation examples.")
    print("Starting AI evaluation...\n")

    report = run_evaluation(dataset, args.delay)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    metrics = report["results"]

    print("\n========== VERIFYAI EVALUATION ==========")
    print(f"Total examples:       {metrics['total_samples']}")
    print(f"Correct predictions:  {metrics['correct_predictions']}")
    print(f"Abstentions:          {metrics['abstentions']}")
    print(f"Coverage:             {metrics['coverage']:.2%}")
    print(f"Accuracy:             {metrics['accuracy']:.2%}")
    print(f"Selective accuracy:   {metrics['selective_accuracy']:.2%}")
    print(f"Macro precision:      {metrics['macro_precision']:.2%}")
    print(f"Macro recall:         {metrics['macro_recall']:.2%}")
    print(f"Macro F1:             {metrics['macro_f1']:.2%}")
    print(f"Successfully evaluated: {metrics['evaluated_samples']}")
    print(f"Provider errors:       {metrics['provider_errors']}")
    print(f"Request success rate:  {metrics['request_success_rate']:.2%}")

    print("\nPer-class results:")

    for label, values in metrics["per_class"].items():
        print(
            f"{label:12} "
            f"Precision={values['precision']:.2f} "
            f"Recall={values['recall']:.2f} "
            f"F1={values['f1']:.2f}"
        )

    print("\nConfusion matrix:")

    for actual, predictions in metrics["confusion_matrix"].items():
        print(f"{actual:12} {predictions}")

    print(f"\nDetailed report saved to: {args.output}")


if __name__ == "__main__":
    main()
