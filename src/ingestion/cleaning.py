from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime
import logging

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import compact_join, normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize papers and return a stable, deduplicated embedding table.

    Drop rows without ID, title, summary or valid publication date. Keep stale
    papers so the quality gate can measure freshness. Naive run dates use UTC.
    For duplicate IDs, keep the most recently updated valid record.
    """
    run_timestamp = pd.Timestamp(run_date)
    if pd.isna(run_timestamp):
        raise ValueError("run_date must be a valid datetime.")
    run_timestamp = (run_timestamp.tz_localize("UTC") if run_timestamp.tzinfo is None
                     else run_timestamp.tz_convert("UTC"))
    df = pd.DataFrame([asdict(record) for record in records],
                      columns=[field.name for field in fields(PaperRecord)])

    def clean_text(value) -> str:
        return normalize_whitespace(value) if isinstance(value, str) else ""

    def clean_list(values) -> list[str]:
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple)):
            return []
        return list(dict.fromkeys(text for value in values if (text := clean_text(value))))

    for column in ("paper_id", "title", "summary", "primary_category", "abs_url", "pdf_url", "comment"):
        df[column] = df[column].map(clean_text)
    for column in ("authors", "categories"):
        df[column] = df[column].map(clean_list)
    df["primary_category"] = [categories[0] if categories else "" for categories in df["categories"]]

    published = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True, format="mixed")
    df["published"] = published
    df["updated"] = updated.fillna(published)
    valid = (df["paper_id"].ne("") & df["title"].ne("") & df["summary"].ne("")
             & published.notna())
    df = df.loc[valid].copy()
    df = (df.sort_values("updated", ascending=False, kind="stable")
          .drop_duplicates("paper_id", keep="first")
          .sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
          .reset_index(drop=True))

    # Calculate calendar-day age; do not mask stale or future publication dates.
    df["age_days"] = (run_timestamp.normalize() - df["published"].dt.normalize()).dt.days.astype("int64")
    for column in ("published", "updated"):
        df[column] = df[column].dt.strftime("%Y-%m-%d")
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len().astype("int64")
    df["text_for_embedding"] = [
        f"Title: {row.title}\nAuthors: {row.authors_joined}\n"
        f"Published: {row.published}\nCategories: {row.categories_joined}\nSummary: {row.summary}"
        for row in df.itertuples(index=False)
    ]
    logging.getLogger(__name__).info("Cleaning: %s input rows -> %s clean rows", len(records), len(df))
    return df
