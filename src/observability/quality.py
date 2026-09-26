from __future__ import annotations

from typing import Any
from pathlib import Path

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate with GX 1.x and save quality plus freshness evidence.

    Lab contract: exactly max_results rows, title >= 8 characters and
    summary >= 50 characters. Overall success includes the freshness SLA.
    The input dataframe is never repaired or changed by this gate.
    """
    name = Path(report_name).stem
    if name.endswith("_quality_report"):
        name = name[:-len("_quality_report")]
    name = safe_slug(name)
    freshness = build_freshness_report(
        df, settings, settings.paths.quality_dir / f"{name}_freshness_report.json"
    )
    required = {"paper_id", "title", "summary", "published", "age_days"}
    missing = sorted(required - set(df.columns))
    # Add absent columns only to the validation copy so GX can report failures.
    validation_df = df.copy(deep=True)
    for column in missing:
        validation_df[column] = None
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name="papers_source")
    asset = source.add_dataframe_asset(name="papers_asset")
    batch_definition = asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": validation_df})
    suite = gx.ExpectationSuite(name="papers_quality")
    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=settings.max_results, max_value=settings.max_results),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="paper_id", min_value=1),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=50),
        gx.expectations.ExpectColumnValuesToMatchRegex(column="paper_id", regex=r"\S"),
        gx.expectations.ExpectColumnValuesToMatchRegex(column="title", regex=r"\S"),
        gx.expectations.ExpectColumnValuesToMatchRegex(column="summary", regex=r"\S"),
    ]
    expectations.extend(gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
                        for column in sorted(required))
    for expectation in expectations:
        suite.add_expectation(expectation)
    result = batch.validate(suite).to_json_dict()
    quality_success = bool(result["success"]) and not missing
    report = {
        "report_name": name,
        "success": quality_success and freshness["is_fresh"],
        "quality_success": quality_success,
        "missing_columns": missing,
        "row_count": len(df),
        "thresholds": {"expected_rows": settings.max_results, "min_title_chars": 8,
                       "min_summary_chars": 50},
        "freshness": freshness,
        "gx_result": result,
    }
    write_json(settings.paths.quality_dir / f"{name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Fail if >25% of rows exceed the age SLA or freshness data is invalid.

    age_days is supplied by cleaning at its run_date; do not recompute against
    the wall clock here. Empty, missing, infinite or future ages fail closed.
    """
    published = pd.to_datetime(
        df.get("published", pd.Series(index=df.index, dtype="object")),
        errors="coerce", utc=True, format="mixed",
    )
    ages = pd.to_numeric(df.get("age_days", pd.Series(index=df.index, dtype="float64")),
                         errors="coerce")
    valid_age = ages.notna() & ~ages.isin([float("inf"), float("-inf")]) & ages.ge(0)
    invalid = ~valid_age | published.isna()
    total_rows = len(df)
    stale_rows = int((valid_age & ages.gt(settings.freshness_threshold_days)).sum())
    stale_ratio = stale_rows / total_rows if total_rows else None
    valid_dates = published.dropna()
    report = {
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "invalid_rows": int(invalid.sum()),
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": bool(total_rows > 0 and not invalid.any() and stale_ratio <= 0.25),
    }
    write_json(Path(report_path), report)
    return report
