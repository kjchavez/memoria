# src/batch/manifest.py
from __future__ import annotations

from datetime import date

from shared.models import TripConfig


def build_day_entry(
    day_date: date,
    day_number: int,
    title: str,
    summary: str,
    journal: list[dict],
    scrapbook: list[dict],
) -> dict:
    label = f"Day {day_number} — {day_date.strftime('%a, %b %d').replace(' 0', ' ')}"
    return {
        "date": day_date.isoformat(),
        "dayNumber": day_number,
        "label": label,
        "title": title,
        "summary": summary,
        "journal": journal,
        "scrapbook": scrapbook,
    }


def build_manifest(config: TripConfig, days: list[dict]) -> dict:
    return {
        "trip": {
            "id": config.id,
            "title": config.title,
            "dates": {
                "start": config.start_date.isoformat(),
                "end": config.end_date.isoformat(),
            },
            "participants": [p.name for p in config.participants],
        },
        "days": days,
    }
