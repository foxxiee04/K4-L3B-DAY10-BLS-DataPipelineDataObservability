from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, normalize_whitespace


def _row_authors_joined(row: dict[str, Any]) -> str:
    if isinstance(row.get("authors_joined"), str) and row["authors_joined"].strip():
        return normalize_whitespace(row["authors_joined"])
    authors = row.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]
    if isinstance(authors, (list, tuple)):
        return compact_join(normalize_whitespace(a) for a in authors if isinstance(a, str) and a.strip())
    return ""


def _row_categories_joined(row: dict[str, Any]) -> str:
    if isinstance(row.get("categories_joined"), str) and row["categories_joined"].strip():
        return normalize_whitespace(row["categories_joined"])
    categories = row.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    if isinstance(categories, (list, tuple)):
        return compact_join(normalize_whitespace(c) for c in categories if isinstance(c, str) and c.strip())
    primary = row.get("primary_category", "")
    return normalize_whitespace(primary) if isinstance(primary, str) else ""


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(student): tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
        - id
        - question_type
        - question
        - ground_truth
        - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if df is None or len(df) == 0:
        raise ValueError("Need at least 1 cleaned document to build test set.")
    if len(df) < 10:
        raise ValueError(f"Need at least 10 cleaned documents, got {len(df)}.")

    required = {"paper_id", "title", "summary"}
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Cleaned dataframe missing required columns: {missing}")

    # Chon 10 paper dai dien, trai deu khap corpus (deterministic).
    clean = df.reset_index(drop=True)
    n = len(clean)
    indices = [round(i * (n - 1) / 9) for i in range(10)]
    # Dam bao khong trung index khi n > 10 (round co the trung khi n nho).
    seen: set[int] = set()
    picked: list[int] = []
    for idx in indices:
        while idx in seen:
            idx = (idx + 1) % n
        seen.add(idx)
        picked.append(idx)

    # Phan bo deu 10 cau qua 4 dang: 3 summary, 3 authors, 2 date, 2 categories.
    question_types = [
        "summary", "authors", "date", "categories",
        "summary", "authors", "date", "categories",
        "summary", "authors",
    ]

    test_set: list[dict[str, Any]] = []
    for seq, (row_idx, qtype) in enumerate(zip(picked, question_types, strict=True), start=1):
        row = clean.iloc[row_idx].to_dict()
        paper_id = normalize_whitespace(str(row.get("paper_id", "")))
        title = normalize_whitespace(str(row.get("title", "")))
        summary = normalize_whitespace(str(row.get("summary", "")))
        published = normalize_whitespace(str(row.get("published", "")))
        if not paper_id or not title or not summary:
            raise ValueError(f"Row {row_idx} missing paper_id/title/summary.")

        if qtype == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(summary)
        elif qtype == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = _row_authors_joined(row)
        elif qtype == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = published
        else:  # categories
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = _row_categories_joined(row)

        if not ground_truth:
            raise ValueError(f"Row {row_idx} has empty ground truth for type '{qtype}'.")
        test_set.append(
            {
                "id": f"eval_{seq:03d}",
                "question_type": qtype,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(test_set, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return test_set
