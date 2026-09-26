from __future__ import annotations

import math

import pandas as pd

from core.utils import write_json


_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "age_days",
    "authors_joined",
    "categories_joined",
    "text_for_embedding",
}


def _rebuild_text_for_embedding(df: pd.DataFrame) -> None:
    """Rebuild embedding text after all corruption operations."""

    def as_text(column: str) -> pd.Series:
        return df[column].fillna("").astype(str)

    df["text_for_embedding"] = (
        "Title: "
        + as_text("title")
        + "\nAuthors: "
        + as_text("authors_joined")
        + "\nPublished: "
        + as_text("published")
        + "\nCategories: "
        + as_text("categories_joined")
        + "\nSummary: "
        + as_text("summary")
    )


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
) -> pd.DataFrame:
    """Create a deterministic corrupted copy of the clean paper dataset.

    Six corruption scenarios are applied:

    1. Drop the latest 20 percent of records.
    2. Blank summaries.
    3. Inject noise into summaries.
    4. Truncate titles to fewer than 8 characters.
    5. Move publication dates 365 days into the past.
    6. Duplicate rows.

    The input dataframe is never modified.
    """
    if df is None or df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    missing_columns = sorted(_REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(
            f"Dataframe missing required columns: {missing_columns}"
        )

    if len(df) < 10:
        raise ValueError(
            f"Need at least 10 rows for the corruption suite, got {len(df)}."
        )

    corrupted = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(corrupted)
    corruption_events: list[dict] = []

    # ------------------------------------------------------------------
    # 1. Drop the latest 20% of records.
    # ------------------------------------------------------------------
    published_dates = pd.to_datetime(
        corrupted["published"],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    drop_count = max(1, math.ceil(input_rows * 0.20))
    drop_indices = (
        published_dates
        .sort_values(ascending=False, na_position="last")
        .head(drop_count)
        .index
        .tolist()
    )
    dropped_ids = (
        corrupted.loc[drop_indices, "paper_id"]
        .astype(str)
        .tolist()
    )

    corrupted = (
        corrupted
        .drop(index=drop_indices)
        .reset_index(drop=True)
    )

    corruption_events.append(
        {
            "type": "drop_latest_records",
            "affected_count": len(dropped_ids),
            "paper_ids": dropped_ids,
            "parameters": {
                "ratio": 0.20,
                "selection": "latest published records",
            },
        }
    )

    remaining_indices = list(corrupted.index)

    # The fixture has 19 rows after dropping five records. These selections
    # are deterministic and disjoint for the normal 24-record lab dataset.
    blank_indices = remaining_indices[0:2]
    noise_indices = remaining_indices[2:4]
    truncate_indices = remaining_indices[4:6]
    duplicate_indices = remaining_indices[6:8]

    # ------------------------------------------------------------------
    # 2. Blank summaries.
    # ------------------------------------------------------------------
    blank_ids = (
        corrupted.loc[blank_indices, "paper_id"]
        .astype(str)
        .tolist()
    )
    corrupted.loc[blank_indices, "summary"] = ""

    if "summary_chars" in corrupted.columns:
        corrupted.loc[blank_indices, "summary_chars"] = 0

    corruption_events.append(
        {
            "type": "blank_summary",
            "affected_count": len(blank_ids),
            "paper_ids": blank_ids,
            "parameters": {
                "replacement": "",
            },
        }
    )

    # ------------------------------------------------------------------
    # 3. Inject visible noise into summaries.
    # ------------------------------------------------------------------
    noise_text = " @@NOISE@@ xqzv_9381 !!! CORRUPTED_TEXT !!!"
    noise_ids = (
        corrupted.loc[noise_indices, "paper_id"]
        .astype(str)
        .tolist()
    )

    corrupted.loc[noise_indices, "summary"] = (
        corrupted.loc[noise_indices, "summary"]
        .fillna("")
        .astype(str)
        + noise_text
    )

    if "summary_chars" in corrupted.columns:
        corrupted.loc[noise_indices, "summary_chars"] = (
            corrupted.loc[noise_indices, "summary"]
            .astype(str)
            .str.len()
        )

    corruption_events.append(
        {
            "type": "inject_noise",
            "affected_count": len(noise_ids),
            "paper_ids": noise_ids,
            "parameters": {
                "noise": noise_text,
            },
        }
    )

    # ------------------------------------------------------------------
    # 4. Truncate titles below the 8-character quality threshold.
    # ------------------------------------------------------------------
    truncate_ids = (
        corrupted.loc[truncate_indices, "paper_id"]
        .astype(str)
        .tolist()
    )

    corrupted.loc[truncate_indices, "title"] = (
        corrupted.loc[truncate_indices, "title"]
        .fillna("")
        .astype(str)
        .str.slice(0, 7)
    )

    corruption_events.append(
        {
            "type": "truncate_title",
            "affected_count": len(truncate_ids),
            "paper_ids": truncate_ids,
            "parameters": {
                "maximum_length": 7,
            },
        }
    )

    # ------------------------------------------------------------------
    # 5. Make at least 30% of remaining records stale.
    #
    # Six stale rows among the final 21 rows give a stale ratio of at
    # least 28.57%, exceeding the configured 25% freshness threshold.
    # ------------------------------------------------------------------
    stale_count = max(1, math.ceil(len(corrupted) * 0.30))
    stale_indices = remaining_indices[-stale_count:]
    stale_ids = (
        corrupted.loc[stale_indices, "paper_id"]
        .astype(str)
        .tolist()
    )

    stale_dates = pd.to_datetime(
        corrupted.loc[stale_indices, "published"],
        errors="raise",
        utc=True,
        format="mixed",
    ) - pd.Timedelta(days=365)

    corrupted.loc[stale_indices, "published"] = (
        stale_dates.dt.strftime("%Y-%m-%d").to_numpy()
    )

    current_ages = pd.to_numeric(
        corrupted.loc[stale_indices, "age_days"],
        errors="raise",
    )
    corrupted.loc[stale_indices, "age_days"] = (
        current_ages + 365
    ).astype("int64").to_numpy()

    corruption_events.append(
        {
            "type": "stale_date",
            "affected_count": len(stale_ids),
            "paper_ids": stale_ids,
            "parameters": {
                "days_shifted": 365,
            },
        }
    )

    # ------------------------------------------------------------------
    # 6. Duplicate rows without changing paper_id.
    #
    # Chroma record IDs remain distinct because retrieval/index.py adds
    # the dataframe position to each internal record ID. Great
    # Expectations will still detect duplicate paper_id values.
    # ------------------------------------------------------------------
    duplicate_ids = (
        corrupted.loc[duplicate_indices, "paper_id"]
        .astype(str)
        .tolist()
    )
    duplicated_rows = corrupted.loc[duplicate_indices].copy(deep=True)

    corrupted = pd.concat(
        [corrupted, duplicated_rows],
        ignore_index=True,
    )

    corruption_events.append(
        {
            "type": "duplicate_rows",
            "affected_count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
            "parameters": {
                "copies_per_selected_row": 1,
            },
        }
    )

    # Rebuild embedding input so the vector index receives the corrupted
    # title, publication date and summary rather than stale clean text.
    _rebuild_text_for_embedding(corrupted)

    # Keep summary_chars consistent with the final summary values.
    if "summary_chars" in corrupted.columns:
        corrupted["summary_chars"] = (
            corrupted["summary"]
            .fillna("")
            .astype(str)
            .str.len()
            .astype("int64")
        )

    corruption_log = {
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "deterministic": True,
        "corruption_count": len(corruption_events),
        "corruptions": corruption_events,
    }
    write_json(output_log_path, corruption_log)

    return corrupted