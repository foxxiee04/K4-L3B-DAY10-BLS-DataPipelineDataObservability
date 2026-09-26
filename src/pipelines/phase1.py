from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


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

    if not quality_report["success"]:
        raise RuntimeError("Baseline quality/freshness failed. Inspect data/quality before indexing.")

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
    generate_phase1_report(
        settings.paths.baseline_report,
        {"row_count": len(df), "collection": index.collection_name, "source": settings.source_api},
        evaluation.summary, quality_report, quality_report["freshness"],
    )

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
    
    