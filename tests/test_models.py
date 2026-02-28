# tests/test_models.py
import pytest
from datetime import date, datetime
from shared.models import Participant, Message, Photo, TripConfig


class TestTripConfig:
    def test_load_from_yaml_dict(self):
        data = {
            "id": "uk-2026",
            "title": "England 2026",
            "destination": "London & Cornwall, England",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "Europe/London",
            "locations": [
                {"name": "South Bank", "lat": 51.5074, "lng": -0.1157},
            ],
            "participants": [
                {"name": "Kevin", "phone": "+15551234567"},
            ],
        }
        config = TripConfig.from_dict(data)
        assert config.id == "uk-2026"
        assert config.title == "England 2026"
        assert config.start_date == date(2026, 5, 21)
        assert config.end_date == date(2026, 5, 28)
        assert config.timezone == "Europe/London"
        assert len(config.locations) == 1
        assert config.locations[0]["name"] == "South Bank"
        assert len(config.participants) == 1
        assert config.participants[0].name == "Kevin"

    def test_day_number_for_date(self):
        data = {
            "id": "uk-2026",
            "title": "England 2026",
            "destination": "London & Cornwall",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "Europe/London",
            "locations": [],
            "participants": [],
        }
        config = TripConfig.from_dict(data)
        assert config.day_number(date(2026, 5, 21)) == 1
        assert config.day_number(date(2026, 5, 22)) == 2
        assert config.day_number(date(2026, 5, 28)) == 8

    def test_day_number_out_of_range_returns_none(self):
        data = {
            "id": "test",
            "title": "Test",
            "destination": "Test",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "UTC",
            "locations": [],
            "participants": [],
        }
        config = TripConfig.from_dict(data)
        assert config.day_number(date(2026, 5, 20)) is None
        assert config.day_number(date(2026, 5, 29)) is None

    def test_find_participant_by_phone(self):
        data = {
            "id": "test",
            "title": "Test",
            "destination": "Test",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "UTC",
            "locations": [],
            "participants": [
                {"name": "Kevin", "phone": "+15551234567"},
                {"name": "Grant", "phone": "+15559876543"},
            ],
        }
        config = TripConfig.from_dict(data)
        assert config.find_participant("+15551234567").name == "Kevin"
        assert config.find_participant("+15559876543").name == "Grant"
        assert config.find_participant("+10000000000") is None


class TestParticipant:
    def test_create(self):
        p = Participant(name="Kevin", phone="+15551234567")
        assert p.name == "Kevin"
        assert p.phone == "+15551234567"


class TestMessage:
    def test_create_text_only(self):
        msg = Message(
            id="msg-1",
            trip_id="uk-2026",
            sender_phone="+15551234567",
            sender_name="Kevin",
            timestamp=datetime(2026, 5, 22, 14, 30, 0),
            text="This is amazing!",
            media_urls=[],
            processed=False,
        )
        assert msg.text == "This is amazing!"
        assert msg.media_urls == []
        assert msg.processed is False

    def test_create_with_media(self):
        msg = Message(
            id="msg-2",
            trip_id="uk-2026",
            sender_phone="+15551234567",
            sender_name="Kevin",
            timestamp=datetime(2026, 5, 22, 14, 30, 0),
            text="Check this out",
            media_urls=["gs://bucket/raw/uk-2026/photo1.jpg"],
            processed=False,
        )
        assert len(msg.media_urls) == 1

    def test_to_dict_and_from_dict_roundtrip(self):
        msg = Message(
            id="msg-1",
            trip_id="uk-2026",
            sender_phone="+15551234567",
            sender_name="Kevin",
            timestamp=datetime(2026, 5, 22, 14, 30, 0),
            text="Hello",
            media_urls=["gs://bucket/raw/photo.jpg"],
            processed=False,
        )
        d = msg.to_dict()
        msg2 = Message.from_dict("msg-1", d)
        assert msg2.id == msg.id
        assert msg2.text == msg.text
        assert msg2.sender_name == msg.sender_name
        assert msg2.timestamp == msg.timestamp
        assert msg2.media_urls == msg.media_urls


class TestPhoto:
    def test_create(self):
        photo = Photo(
            url="processed/large/20260522_143022_kevin.jpg",
            thumb="processed/thumb/20260522_143022_kevin.jpg",
            caption="A lovely view from the Globe.",
            alt="View from Shakespeare's Globe Theatre",
            by="Kevin",
            time="14:30",
            location="Shakespeare's Globe",
            category="sightseeing",
            quality=8,
        )
        assert photo.quality == 8
        assert photo.category == "sightseeing"

    def test_to_dict(self):
        photo = Photo(
            url="processed/large/photo.jpg",
            thumb="processed/thumb/photo.jpg",
            caption="A caption",
            alt="Alt text",
            by="Kevin",
            time="14:30",
            location="London",
            category="sightseeing",
            quality=7,
        )
        d = photo.to_dict()
        assert d["type"] == "photo"
        assert d["url"] == "processed/large/photo.jpg"
        assert d["quality"] == 7
