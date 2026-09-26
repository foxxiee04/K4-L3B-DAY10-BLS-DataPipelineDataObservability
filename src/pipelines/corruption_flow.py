from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


_METRIC_NAMES = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _require_artifacts(paths: list[Path]) -> None:
    """Fail early when phase-1 artifacts are unavailable."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Required baseline artifacts are missing:\n"
            f"{formatted}\n"
            "Run script/run_phase1.py before the corruption flow."
        )


def _load_dataframe(path: Path) -> pd.DataFrame:
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Expected a non-empty record list in {path}.")

    return pd.DataFrame(payload)


def _save_dataframe(
    df: pd.DataFrame,
    csv_path: Path,
    json_path: Path,
) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def repair_from_raw_snapshot(
    settings: Settings,
    run_date,
) -> pd.DataFrame:
    """Rebuild trusted clean data from the immutable raw snapshot.

    This function never repairs the corrupted dataframe in place. Repeated
    calls with the same raw snapshot and run_date produce the same result.
    """
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(
        raw_records,
        run_date=run_date,
    )

    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    return repaired_df


def _format_metric(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "N/A"


def _print_comparison(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
) -> None:
    print()
    print("=== Baseline vs Corrupted vs Repaired ===")
    print(
        f"{'Metric':<28}"
        f"{'Baseline':>12}"
        f"{'Corrupted':>12}"
        f"{'Repaired':>12}"
    )
    print("-" * 64)

    for metric_name in _METRIC_NAMES:
        print(
            f"{metric_name:<28}"
            f"{_format_metric(baseline_metrics.get(metric_name)):>12}"
            f"{_format_metric(corrupted_metrics.get(metric_name)):>12}"
            f"{_format_metric(repaired_metrics.get(metric_name)):>12}"
        )


def run_corruption_flow_pipeline(
    settings: Settings,
) -> dict[str, Any]:
    """Run corruption, evaluation, raw-snapshot repair and comparison."""
    _require_artifacts(
        [
            settings.paths.clean_json,
            settings.paths.raw_records_json,
            settings.paths.eval_testset,
            settings.paths.baseline_metrics,
            settings.paths.baseline_quality_report,
        ]
    )

    # Use one timestamp for the complete repair flow. This keeps age_days
    # deterministic inside a single run.
    run_date = now_utc()

    print("[1/10] Loading baseline artifacts...")
    baseline_df = _load_dataframe(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(
        settings.paths.baseline_quality_report
    )
    baseline_freshness = baseline_quality.get("freshness", {})

    print(f"       Baseline rows: {len(baseline_df)}")
    print(
        "       Baseline hit rate:",
        baseline_metrics.get("retrieval_hit_rate"),
    )

    # --------------------------------------------------------------
    # Corrupted state
    # --------------------------------------------------------------
    print("[2/10] Applying six corruption scenarios...")
    corrupted_df = corrupt_clean_dataframe(
        baseline_df,
        settings.paths.corruption_log,
    )

    # Verify that corruption did not mutate the baseline dataframe.
    if len(baseline_df) != baseline_quality.get(
        "row_count",
        len(baseline_df),
    ):
        raise RuntimeError(
            "The corruption function appears to have mutated baseline data."
        )

    print(f"       Corrupted rows: {len(corrupted_df)}")
    print(f"       Corruption log: {settings.paths.corruption_log}")

    print("[3/10] Saving corrupted artifacts...")
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    print("[4/10] Running corrupted quality checks...")
    corrupted_quality = run_data_quality_checks(
        corrupted_df,
        settings,
        "corrupted_quality_report",
    )
    corrupted_freshness = corrupted_quality.get("freshness", {})

    print(
        "       Corrupted quality success:",
        corrupted_quality.get("quality_success"),
    )
    print(
        "       Corrupted freshness success:",
        corrupted_freshness.get("is_fresh"),
    )

    print("[5/10] Building and evaluating corrupted index...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        settings.paths.corrupted_embeddings_json,
    )

    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_evaluation.summary

    # --------------------------------------------------------------
    # Repaired state
    # --------------------------------------------------------------
    print("[6/10] Repairing from trusted raw snapshot...")
    repaired_df = repair_from_raw_snapshot(
        settings,
        run_date=run_date,
    )
    print(f"       Repaired rows: {len(repaired_df)}")

    print("[7/10] Running repaired quality checks...")
    repaired_quality = run_data_quality_checks(
        repaired_df,
        settings,
        "repaired_quality_report",
    )
    repaired_freshness = repaired_quality.get("freshness", {})

    print(
        "       Repaired quality success:",
        repaired_quality.get("quality_success"),
    )
    print(
        "       Repaired freshness success:",
        repaired_freshness.get("is_fresh"),
    )

    print("[8/10] Building repaired Chroma index...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        settings.paths.repaired_embeddings_json,
    )

    print("[9/10] Evaluating repaired data...")
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_evaluation.summary

    print("[10/10] Writing comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )

    _print_comparison(
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
    )

    if corrupted_quality.get("success"):
        print(
            "WARNING: Corrupted data unexpectedly passed the quality gate."
        )

    if not repaired_quality.get("success"):
        print(
            "WARNING: Repaired data did not fully pass the quality gate."
        )

    baseline_hit = baseline_metrics.get("retrieval_hit_rate")
    corrupted_hit = corrupted_metrics.get("retrieval_hit_rate")
    if (
        isinstance(baseline_hit, (int, float))
        and isinstance(corrupted_hit, (int, float))
        and corrupted_hit >= baseline_hit
    ):
        print(
            "WARNING: Retrieval hit rate did not decline after corruption."
        )

    print()
    print("=== Corruption flow completed ===")
    print(f"Corrupted metrics: {settings.paths.corrupted_metrics}")
    print(f"Repaired metrics: {settings.paths.repaired_metrics}")
    print(f"Comparison report: {settings.paths.comparison_report}")

    return {
        "baseline": {
            "metrics": baseline_metrics,
            "quality": baseline_quality,
            "freshness": baseline_freshness,
        },
        "corrupted": {
            "metrics": corrupted_metrics,
            "quality": corrupted_quality,
            "freshness": corrupted_freshness,
        },
        "repaired": {
            "metrics": repaired_metrics,
            "quality": repaired_quality,
            "freshness": repaired_freshness,
        },
    }


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)


if __name__ == "__main__":
    main()