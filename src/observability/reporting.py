from __future__ import annotations

from typing import Any
from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write baseline evidence from the current pipeline run."""
    lines = ["# Phase 1 Baseline Report", "", "## Dataset", ""]
    lines.extend(f"- {key}: {value}" for key, value in source_summary.items())
    lines.extend(["", "## Quality and Freshness", "",
                  f"- Overall success: {quality.get('success')}",
                  f"- GX quality success: {quality.get('quality_success')}",
                  f"- Freshness success: {freshness.get('is_fresh')}",
                  f"- Stale rows: {freshness.get('stale_rows')}",
                  f"- Stale ratio: {freshness.get('stale_ratio')}",
                  "", "## Evaluation", ""])
    lines.extend(f"- {key}: {value}" for key, value in metrics.items())
    lines.extend(["", "Use the same evaluation contract and test set for corruption and repair.",
                  "Mock answers and heuristic judges are not evidence of LLM-agent execution.", ""])
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Write the Baseline vs Corrupted vs Repaired comparison."""

    baseline_quality = baseline_quality or {}
    baseline_freshness = (
        baseline_freshness
        or baseline_quality.get("freshness", {})
    )

    def format_value(value: Any) -> str:
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return f"{float(value):.4f}"
        if value is None:
            return "N/A"
        return str(value)

    def metric_change(
        first: dict[str, Any],
        second: dict[str, Any],
        metric_name: str,
    ) -> str:
        first_value = first.get(metric_name)
        second_value = second.get(metric_name)

        if not isinstance(first_value, (int, float)):
            return "N/A"
        if not isinstance(second_value, (int, float)):
            return "N/A"

        return f"{float(second_value - first_value):+.4f}"

    metric_names = (
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    )

    lines = [
        "# Corruption and Repair Comparison Report",
        "",
        "## Overview",
        "",
        (
            "This report compares the same evaluation set across the "
            "clean baseline, deliberately corrupted data, and data "
            "repaired from the trusted raw snapshot."
        ),
        "",
        "## RAG Metrics",
        "",
        (
            "| Metric | Baseline | Corrupted | Repaired | "
            "Corruption change | Recovery change |"
        ),
        "|---|---:|---:|---:|---:|---:|",
    ]
    lines[2:2] = ["## Evaluation configuration", "",
                  f"- Baseline: {baseline_metrics.get('evaluation_contract', 'Legacy run: configuration not recorded')}",
                  f"- Corrupted: {corrupted_metrics.get('evaluation_contract', 'Legacy run: configuration not recorded')}",
                  f"- Repaired: {repaired_metrics.get('evaluation_contract', 'Legacy run: configuration not recorded')}", ""]

    for metric_name in metric_names:
        lines.append(
            "| "
            f"`{metric_name}`"
            " | "
            f"{format_value(baseline_metrics.get(metric_name))}"
            " | "
            f"{format_value(corrupted_metrics.get(metric_name))}"
            " | "
            f"{format_value(repaired_metrics.get(metric_name))}"
            " | "
            f"{metric_change(baseline_metrics, corrupted_metrics, metric_name)}"
            " | "
            f"{metric_change(corrupted_metrics, repaired_metrics, metric_name)}"
            " |"
        )

    lines.extend(
        [
            "",
            "## Data Quality and Freshness",
            "",
            (
                "| Signal | Baseline | Corrupted | Repaired |"
            ),
            "|---|---:|---:|---:|",
            (
                "| Overall quality gate "
                f"| {format_value(baseline_quality.get('success'))} "
                f"| {format_value(corrupted_quality.get('success'))} "
                f"| {format_value(repaired_quality.get('success'))} |"
            ),
            (
                "| GX quality checks "
                f"| {format_value(baseline_quality.get('quality_success'))} "
                f"| {format_value(corrupted_quality.get('quality_success'))} "
                f"| {format_value(repaired_quality.get('quality_success'))} |"
            ),
            (
                "| Row count "
                f"| {format_value(baseline_quality.get('row_count'))} "
                f"| {format_value(corrupted_quality.get('row_count'))} "
                f"| {format_value(repaired_quality.get('row_count'))} |"
            ),
            (
                "| Freshness status "
                f"| {format_value(baseline_freshness.get('is_fresh'))} "
                f"| {format_value(corrupted_freshness.get('is_fresh'))} "
                f"| {format_value(repaired_freshness.get('is_fresh'))} |"
            ),
            (
                "| Stale rows "
                f"| {format_value(baseline_freshness.get('stale_rows'))} "
                f"| {format_value(corrupted_freshness.get('stale_rows'))} "
                f"| {format_value(repaired_freshness.get('stale_rows'))} |"
            ),
            (
                "| Stale ratio "
                f"| {format_value(baseline_freshness.get('stale_ratio'))} "
                f"| {format_value(corrupted_freshness.get('stale_ratio'))} "
                f"| {format_value(repaired_freshness.get('stale_ratio'))} |"
            ),
            "",
            "## Impact Analysis",
            "",
        ]
    )

    baseline_hit = baseline_metrics.get("retrieval_hit_rate")
    corrupted_hit = corrupted_metrics.get("retrieval_hit_rate")
    repaired_hit = repaired_metrics.get("retrieval_hit_rate")

    baseline_f1 = baseline_metrics.get("mean_token_f1")
    corrupted_f1 = corrupted_metrics.get("mean_token_f1")
    repaired_f1 = repaired_metrics.get("mean_token_f1")

    lines.extend(
        [
            (
                "- Retrieval hit-rate change after corruption: "
                f"{metric_change(baseline_metrics, corrupted_metrics, 'retrieval_hit_rate')}."
            ),
            (
                "- Retrieval hit-rate recovery: "
                f"{metric_change(corrupted_metrics, repaired_metrics, 'retrieval_hit_rate')}."
            ),
            (
                "- Mean token-F1 change after corruption: "
                f"{metric_change(baseline_metrics, corrupted_metrics, 'mean_token_f1')}."
            ),
            (
                "- Mean token-F1 recovery: "
                f"{metric_change(corrupted_metrics, repaired_metrics, 'mean_token_f1')}."
            ),
            "",
            "## Interpretation",
            "",
        ]
    )

    if (
        isinstance(baseline_hit, (int, float))
        and isinstance(corrupted_hit, (int, float))
        and corrupted_hit < baseline_hit
    ):
        lines.append(
            "- Removing or damaging indexed documents reduced retrieval "
            "coverage on the unchanged benchmark."
        )
    else:
        lines.append(
            "- Retrieval hit rate did not decline. Review whether corrupted "
            "records overlap with benchmark document IDs."
        )

    if not corrupted_quality.get("success"):
        lines.append(
            "- The quality gate detected the deliberately corrupted state."
        )
    else:
        lines.append(
            "- The corrupted dataset unexpectedly passed the quality gate; "
            "the corruption selection or expectations should be reviewed."
        )

    if repaired_quality.get("success"):
        lines.append(
            "- Rebuilding from the raw snapshot restored the expected "
            "quality and freshness state."
        )
    else:
        lines.append(
            "- The repaired dataset still violates at least one quality or "
            "freshness expectation."
        )

    if (
        isinstance(baseline_hit, (int, float))
        and isinstance(repaired_hit, (int, float))
        and isinstance(baseline_f1, (int, float))
        and isinstance(repaired_f1, (int, float))
        and repaired_hit == baseline_hit
        and repaired_f1 == baseline_f1
    ):
        lines.append(
            "- Repaired retrieval and answer metrics fully recovered to "
            "the clean baseline."
        )
    else:
        lines.append(
            "- Repaired metrics did not exactly match baseline; inspect "
            "the repaired index, evaluation answers and run configuration."
        )

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- Corruption log: `data/results/corruption_log.json`",
            "- Corrupted metrics: `data/results/corrupted_metrics.json`",
            "- Repaired metrics: `data/results/repaired_metrics.json`",
            "- Corrupted quality: `data/quality/corrupted_quality_report.json`",
            "- Repaired quality: `data/quality/repaired_quality_report.json`",
            "",
        ]
    )

    write_text(report_path, "\n".join(lines))
