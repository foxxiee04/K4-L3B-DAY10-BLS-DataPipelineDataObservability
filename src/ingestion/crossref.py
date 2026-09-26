from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
import logging
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


def _text(value) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", value)))


def _date(value) -> str:
    if not isinstance(value, dict):
        return ""
    try:
        parts = value["date-parts"][0]
        return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1,
                    int(parts[2]) if len(parts) > 2 else 1).isoformat()
    except (KeyError, IndexError, TypeError, ValueError):
        try:
            return date.fromisoformat(value["date-time"][:10]).isoformat()
        except (KeyError, TypeError, ValueError):
            return ""


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise ValueError("Crossref payload must contain a message object.")
    items = payload["message"].get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref message.items must be a list.")
    records = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = _text(item.get("DOI"))
        titles = item.get("title") or []
        title = _text(titles[0] if isinstance(titles, list) and titles else titles)
        if not paper_id or not title:
            continue
        authors = []
        for author in item.get("author") or []:
            if isinstance(author, dict):
                name = _text(author.get("name")) or normalize_whitespace(
                    f"{_text(author.get('given'))} {_text(author.get('family'))}"
                )
                if name:
                    authors.append(name)
        subjects = item.get("subject") or []
        if isinstance(subjects, str):
            subjects = [subjects]
        categories = [text for value in subjects if (text := _text(value))]
        published = next((parsed for key in ("published", "published-print", "published-online", "issued")
                          if (parsed := _date(item.get(key)))), "")
        pdf_url = next((_text(link.get("URL")) for link in item.get("link") or []
                        if isinstance(link, dict) and link.get("content-type") == "application/pdf"), "")
        records.append(PaperRecord(
            paper_id=paper_id, title=title, summary=_text(item.get("abstract")),
            authors=authors, categories=categories,
            primary_category=categories[0] if categories else "",
            published=published, updated=_date(item.get("deposited")) or _date(item.get("created")) or published,
            abs_url=_text(item.get("URL")) or f"https://doi.org/{paper_id}",
            pdf_url=pdf_url, comment=f"Crossref record {paper_id}",
        ))
    if len(records) != len(items):
        logger.warning("Skipped %s records missing a valid DOI/title.", len(items) - len(records))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Doc snapshot hoac goi API voi retry/fallback, sau do luu records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    def parse_source(payload):
        records = parse_crossref_payload(payload)[:settings.max_results]
        if not records:
            raise ValueError("Source contains no usable papers.")
        return records

    if settings.max_results <= 0:
        raise ValueError("max_results must be positive.")
    snapshot = settings.paths.raw_api_response
    records = None
    if not settings.refresh_source and snapshot.exists():
        try:
            records = parse_source(read_json(snapshot))
        except (OSError, ValueError) as exc:
            logger.warning("Snapshot unavailable; trying API: %s", exc)

    if records is None:
        for attempt in range(3):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params={"query": settings.source_query, "filter": settings.source_filter,
                            "rows": settings.max_results},
                    headers={"User-Agent": "Day10-DataObservability-Lab/1.0"},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                records = parse_source(payload)
            except (requests.RequestException, ValueError) as exc:
                logger.warning("Crossref attempt %s/3 failed: %s", attempt + 1, exc)
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status != 429 and status < 500:
                    break
                if attempt < 2:
                    time.sleep(2 ** attempt)
            else:
                # Preserve the previous snapshot until the new payload is usable.
                write_json(snapshot, payload)
                break
        if records is None:
            logger.warning("API unavailable; falling back to snapshot: %s", snapshot)
            try:
                records = parse_source(read_json(snapshot))
            except (OSError, ValueError) as exc:
                raise RuntimeError("Crossref API and local response snapshot are unavailable.") from exc

    if len(records) < settings.max_results:
        logger.warning("Only %s/%s usable papers returned.", len(records), settings.max_results)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    rows = read_json(path)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Expected a non-empty record list in {path}.")
    try:
        return [PaperRecord(**row) for row in rows]
    except TypeError as exc:
        raise ValueError(f"Invalid PaperRecord schema in {path}.") from exc
