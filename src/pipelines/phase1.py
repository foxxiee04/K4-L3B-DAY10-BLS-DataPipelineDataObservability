from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json, write_text
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def _build_report(
    *,
    row_count: int,
    quality_report: dict,
    metrics: dict,
    collection_name: str,
) -> str:
    freshness = quality_report.get("freshness", {})

    return f"""# Phase 1 Baseline Report

## Dataset

- Clean papers: {row_count}
- Chroma collection: `{collection_name}`

## Data Quality

- Overall success: {quality_report.get("success")}
- Quality success: {quality_report.get("quality_success")}
- Freshness success: {freshness.get("is_fresh")}
- Stale rows: {freshness.get("stale_rows")}
- Stale ratio: {freshness.get("stale_ratio")}
- Freshness threshold: {freshness.get("threshold_days")} days

## RAG Evaluation

- Samples: {metrics.get("samples")}
- Retrieval hit rate: {metrics.get("retrieval_hit_rate")}
- Mean token F1: {metrics.get("mean_token_f1")}
- Judge accuracy: {metrics.get("judge_accuracy")}
- Mean judge score: {metrics.get("mean_judge_score")}

## Ragas

{metrics.get("ragas")}

## Conclusion

This report records the clean baseline before controlled data corruption.
The same evaluation set should be reused for corrupted and repaired runs.
"""


def main() -> None:
    settings = load_settings()

    print("[1/7] Loading source records...")
    records = fetch_source_records(settings)
    print(f"      Loaded {len(records)} raw records.")

    print("[2/7] Cleaning data...")
    df = build_clean_dataframe(records, run_date=now_utc())

    write_csv(df, settings.paths.clean_csv)

    # JSON cannot reliably serialize every pandas/numpy value directly,
    # so use DataFrame's JSON-compatible representation.
    clean_records = df.to_dict(orient="records")
    write_json(settings.paths.clean_json, clean_records)

    print(f"      Clean rows: {len(df)}")
    print(f"      CSV: {settings.paths.clean_csv}")
    print(f"      JSON: {settings.paths.clean_json}")

    print("[3/7] Running quality and freshness checks...")
    quality_report = run_data_quality_checks(
        df,
        settings,
        "baseline_quality_report",
    )

    print(f"      Quality success: {quality_report.get('quality_success')}")
    print(
        "      Freshness success:",
        quality_report.get("freshness", {}).get("is_fresh"),
    )

    print("[4/7] Building baseline Chroma index...")
    index = LocalEmbeddingIndex.build(
        df,
        settings,
        settings.paths.embeddings_json,
    )

    print(f"      Collection: {index.collection_name}")
    print(f"      Indexed documents: {len(index.documents)}")

    print("[5/7] Preparing evaluation test set...")
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"      Reusing: {settings.paths.eval_testset}")
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
        print(f"      Generated {len(test_set)} questions.")

    print("[6/7] Evaluating baseline RAG...")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    print("[7/7] Writing baseline report...")
    report = _build_report(
        row_count=len(df),
        quality_report=quality_report,
        metrics=evaluation.summary,
        collection_name=index.collection_name,
    )

    write_text(settings.paths.baseline_report, report)

    print()
    print("=== Phase 1 baseline completed ===")
    print(f"Clean rows: {len(df)}")
    print(f"Quality success: {quality_report.get('success')}")
    print(
        f"Retrieval hit rate: "
        f"{evaluation.summary.get('retrieval_hit_rate')}"
    )
    print(
        f"Mean token F1: "
        f"{evaluation.summary.get('mean_token_f1')}"
    )
    print(f"Metrics: {settings.paths.baseline_metrics}")
    print(f"Answers: {settings.paths.baseline_answers}")
    print(f"Report: {settings.paths.baseline_report}")


if __name__ == "__main__":
    main()
    
    