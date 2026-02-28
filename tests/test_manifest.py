# tests/test_manifest.py
import pytest
import json
from datetime import date
from batch.manifest import build_manifest, build_day_entry
from shared.models import TripConfig


@pytest.fixture
def trip_config():
    return TripConfig.from_dict({
        "id": "uk-2026",
        "title": "England 2026",
        "destination": "London & Cornwall",
        "dates": {"start": "2026-05-21", "end": "2026-05-28"},
        "timezone": "Europe/London",
        "locations": [],
        "participants": [
            {"name": "Kevin", "phone": "+15551234567"},
            {"name": "Grant", "phone": "+15559876543"},
        ],
    })


class TestBuildDayEntry:
    def test_basic_day_entry(self):
        journal_items = [
            {
                "type": "photo",
                "url": "processed/large/photo1.jpg",
                "thumb": "processed/thumb/photo1.jpg",
                "caption": "A lovely view",
                "alt": "Thames view",
                "by": "Kevin",
                "time": "14:30",
                "location": "South Bank",
                "category": "sightseeing",
                "quality": 8,
            }
        ]
        scrapbook_items = journal_items + [
            {
                "type": "photo",
                "url": "processed/large/photo2.jpg",
                "thumb": "processed/thumb/photo2.jpg",
                "caption": "Cheese at Borough Market",
                "alt": "Cheese wheels",
                "by": "Kevin",
                "time": "10:15",
                "location": "Borough Market",
                "category": "food",
                "quality": 6,
            }
        ]
        entry = build_day_entry(
            day_date=date(2026, 5, 22),
            day_number=2,
            title="Theatre Night",
            summary="A wonderful day exploring London.",
            journal=journal_items,
            scrapbook=scrapbook_items,
        )
        assert entry["date"] == "2026-05-22"
        assert entry["dayNumber"] == 2
        assert entry["title"] == "Theatre Night"
        assert "Fri, May 22" in entry["label"]
        assert len(entry["journal"]) == 1
        assert len(entry["scrapbook"]) == 2


class TestBuildManifest:
    def test_builds_valid_manifest(self, trip_config):
        days = [
            build_day_entry(
                day_date=date(2026, 5, 22),
                day_number=2,
                title="Theatre Night",
                summary="Explored London and saw a show.",
                journal=[],
                scrapbook=[],
            )
        ]
        manifest = build_manifest(trip_config, days)
        assert manifest["trip"]["id"] == "uk-2026"
        assert manifest["trip"]["title"] == "England 2026"
        assert manifest["trip"]["dates"]["start"] == "2026-05-21"
        assert manifest["trip"]["dates"]["end"] == "2026-05-28"
        assert "Kevin" in manifest["trip"]["participants"]
        assert len(manifest["days"]) == 1

    def test_manifest_serializes_to_json(self, trip_config):
        manifest = build_manifest(trip_config, [])
        json_str = json.dumps(manifest)
        parsed = json.loads(json_str)
        assert parsed["trip"]["id"] == "uk-2026"
