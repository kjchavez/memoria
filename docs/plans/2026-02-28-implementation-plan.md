# Memoria Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete Memoria trip memories engine — from SMS ingestion through AI curation to static frontend rendering.

**Architecture:** Three layers: (1) a Flask webhook handler on Cloud Run receives Twilio SMS/MMS and stores raw media in GCS + metadata in Firestore, (2) a nightly batch job does EXIF extraction, image resizing, Claude vision analysis, curation, and manifest generation, (3) a vanilla JS frontend renders the curated journal and full scrapbook from `manifest.json`. All GCP infra managed by Terraform.

**Tech Stack:** Python 3.12+, Flask, uv, Pillow, anthropic SDK, google-cloud-storage, google-cloud-firestore, Terraform, vanilla JS, pytest

---

## Phase 1: Project Foundation

### Task 1: Python project setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/shared/__init__.py`
- Create: `src/webhook/__init__.py`
- Create: `src/batch/__init__.py`
- Create: `src/export/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "memoria"
version = "0.1.0"
description = "Trip memories engine — SMS photos in, curated journal out"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0",
    "twilio>=9.0",
    "google-cloud-storage>=2.14",
    "google-cloud-firestore>=2.16",
    "anthropic>=0.40",
    "pillow>=10.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "gunicorn>=22.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

**Step 2: Create .env.example**

```
# GCP
GCP_PROJECT_ID=
GCS_BUCKET_NAME=

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=

# Claude API
ANTHROPIC_API_KEY=

# Trip
ACTIVE_TRIP_ID=uk-2026
```

**Step 3: Create all `__init__.py` files and `tests/conftest.py`**

Empty `__init__.py` files for: `src/`, `src/shared/`, `src/webhook/`, `src/batch/`, `src/export/`, `tests/`.

`tests/conftest.py`:
```python
import pytest
```

**Step 4: Initialize uv and install dependencies**

Run: `cd /home/ad.dex.ai/kevin/thirdparty/memoria && uv sync`

**Step 5: Verify pytest runs (zero tests, no errors)**

Run: `uv run pytest -v`
Expected: "no tests ran" with exit code 5 (no tests collected), no import errors

**Step 6: Commit**

```bash
git add pyproject.toml .env.example src/ tests/conftest.py
git commit -m "chore: initialize Python project with uv and dependencies"
```

---

### Task 2: Shared data models

**Files:**
- Create: `src/shared/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing tests**

```python
# tests/test_models.py
import pytest
from datetime import date, datetime
from shared.models import Trip, Participant, Message, Photo, TripConfig


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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.models'`

**Step 3: Write minimal implementation**

```python
# src/shared/models.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime


@dataclass
class Participant:
    name: str
    phone: str


@dataclass
class TripConfig:
    id: str
    title: str
    destination: str
    start_date: date
    end_date: date
    timezone: str
    locations: list[dict]
    participants: list[Participant]

    @classmethod
    def from_dict(cls, data: dict) -> TripConfig:
        return cls(
            id=data["id"],
            title=data["title"],
            destination=data["destination"],
            start_date=date.fromisoformat(str(data["dates"]["start"])),
            end_date=date.fromisoformat(str(data["dates"]["end"])),
            timezone=data["timezone"],
            locations=data.get("locations", []),
            participants=[
                Participant(name=p["name"], phone=p.get("phone", ""))
                for p in data.get("participants", [])
            ],
        )

    def day_number(self, d: date) -> int | None:
        """Return 1-indexed day number, or None if date is outside trip range."""
        delta = (d - self.start_date).days
        if delta < 0 or d > self.end_date:
            return None
        return delta + 1

    def find_participant(self, phone: str) -> Participant | None:
        for p in self.participants:
            if p.phone == phone:
                return p
        return None


@dataclass
class Message:
    id: str
    trip_id: str
    sender_phone: str
    sender_name: str
    timestamp: datetime
    text: str | None
    media_urls: list[str]
    processed: bool

    def to_dict(self) -> dict:
        return {
            "trip_id": self.trip_id,
            "sender_phone": self.sender_phone,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "media_urls": self.media_urls,
            "processed": self.processed,
        }

    @classmethod
    def from_dict(cls, doc_id: str, data: dict) -> Message:
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            id=doc_id,
            trip_id=data["trip_id"],
            sender_phone=data["sender_phone"],
            sender_name=data["sender_name"],
            timestamp=ts,
            text=data.get("text"),
            media_urls=data.get("media_urls", []),
            processed=data.get("processed", False),
        )


@dataclass
class Photo:
    url: str
    thumb: str
    caption: str
    alt: str
    by: str
    time: str
    location: str
    category: str
    quality: int

    def to_dict(self) -> dict:
        return {
            "type": "photo",
            "url": self.url,
            "thumb": self.thumb,
            "caption": self.caption,
            "alt": self.alt,
            "by": self.by,
            "time": self.time,
            "location": self.location,
            "category": self.category,
            "quality": self.quality,
        }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/shared/models.py tests/test_models.py
git commit -m "feat: add shared data models (TripConfig, Participant, Message, Photo)"
```

---

### Task 3: Trip config loader (YAML)

**Files:**
- Create: `src/shared/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing tests**

```python
# tests/test_config.py
import pytest
from pathlib import Path
from shared.config import load_trip_config


TRIPS_DIR = Path(__file__).parent.parent / "trips"


class TestLoadTripConfig:
    def test_load_uk_2026(self):
        config = load_trip_config(TRIPS_DIR / "uk-2026" / "trip.yaml")
        assert config.id == "uk-2026"
        assert config.title == "England 2026"
        assert config.destination == "London & Cornwall, England"
        assert config.timezone == "Europe/London"
        assert len(config.locations) >= 10
        assert len(config.participants) == 4
        participant_names = [p.name for p in config.participants]
        assert "Elizabeth" in participant_names
        assert "Kevin" in participant_names

    def test_load_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_trip_config(Path("/nonexistent/trip.yaml"))
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/shared/config.py
from pathlib import Path

import yaml

from shared.models import TripConfig


def load_trip_config(path: Path) -> TripConfig:
    """Load a trip configuration from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return TripConfig.from_dict(data)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/shared/config.py tests/test_config.py
git commit -m "feat: add trip config YAML loader"
```

---

## Phase 2: Webhook Handler

### Task 4: Twilio webhook request parsing

**Files:**
- Create: `src/webhook/twilio_handler.py`
- Create: `tests/test_webhook.py`

**Step 1: Write the failing tests**

```python
# tests/test_webhook.py
import pytest
from webhook.twilio_handler import parse_twilio_request, TwilioMessage


class TestParseTwilioRequest:
    def test_parse_text_only_message(self):
        form_data = {
            "From": "+15551234567",
            "Body": "Just landed!",
            "NumMedia": "0",
            "MessageSid": "SM1234567890",
        }
        msg = parse_twilio_request(form_data)
        assert msg.sender == "+15551234567"
        assert msg.body == "Just landed!"
        assert msg.media_urls == []
        assert msg.message_sid == "SM1234567890"

    def test_parse_message_with_one_photo(self):
        form_data = {
            "From": "+15551234567",
            "Body": "Check this out!",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/123.jpg",
            "MediaContentType0": "image/jpeg",
            "MessageSid": "SM9876543210",
        }
        msg = parse_twilio_request(form_data)
        assert len(msg.media_urls) == 1
        assert msg.media_urls[0] == "https://api.twilio.com/media/123.jpg"
        assert msg.media_content_types[0] == "image/jpeg"

    def test_parse_message_with_multiple_photos(self):
        form_data = {
            "From": "+15559876543",
            "Body": "",
            "NumMedia": "2",
            "MediaUrl0": "https://api.twilio.com/media/a.jpg",
            "MediaContentType0": "image/jpeg",
            "MediaUrl1": "https://api.twilio.com/media/b.png",
            "MediaContentType1": "image/png",
            "MessageSid": "SM1111111111",
        }
        msg = parse_twilio_request(form_data)
        assert len(msg.media_urls) == 2
        assert msg.body == ""

    def test_parse_empty_body_and_no_media(self):
        form_data = {
            "From": "+15551234567",
            "Body": "",
            "NumMedia": "0",
            "MessageSid": "SM0000000000",
        }
        msg = parse_twilio_request(form_data)
        assert msg.body == ""
        assert msg.media_urls == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_webhook.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/webhook/twilio_handler.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TwilioMessage:
    sender: str
    body: str
    media_urls: list[str]
    media_content_types: list[str]
    message_sid: str


def parse_twilio_request(form_data: dict) -> TwilioMessage:
    """Parse a Twilio webhook POST form into a TwilioMessage."""
    num_media = int(form_data.get("NumMedia", "0"))
    media_urls = []
    media_content_types = []
    for i in range(num_media):
        url = form_data.get(f"MediaUrl{i}")
        content_type = form_data.get(f"MediaContentType{i}", "")
        if url:
            media_urls.append(url)
            media_content_types.append(content_type)

    return TwilioMessage(
        sender=form_data.get("From", ""),
        body=form_data.get("Body", ""),
        media_urls=media_urls,
        media_content_types=media_content_types,
        message_sid=form_data.get("MessageSid", ""),
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_webhook.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/webhook/twilio_handler.py tests/test_webhook.py
git commit -m "feat: add Twilio webhook request parser"
```

---

### Task 5: Webhook Flask app

**Files:**
- Create: `src/webhook/main.py`
- Modify: `tests/test_webhook.py` (add Flask app tests)
- Create: `src/webhook/Dockerfile`
- Create: `src/webhook/requirements.txt`

**Step 1: Write the failing tests (add to test_webhook.py)**

```python
# Append to tests/test_webhook.py
import json
from unittest.mock import patch, MagicMock
from webhook.main import create_app


@pytest.fixture
def app():
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestWebhookEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"

    @patch("webhook.main.process_incoming_message")
    def test_incoming_sms_from_known_participant(self, mock_process, client):
        mock_process.return_value = None
        resp = client.post(
            "/webhook/sms",
            data={
                "From": "+15551234567",
                "Body": "Just landed!",
                "NumMedia": "0",
                "MessageSid": "SM123",
            },
        )
        assert resp.status_code == 200
        assert "twiml" in resp.content_type.lower() or resp.status_code == 200
        mock_process.assert_called_once()

    @patch("webhook.main.process_incoming_message")
    def test_incoming_mms_with_photo(self, mock_process, client):
        mock_process.return_value = None
        resp = client.post(
            "/webhook/sms",
            data={
                "From": "+15551234567",
                "Body": "Look!",
                "NumMedia": "1",
                "MediaUrl0": "https://api.twilio.com/media/123.jpg",
                "MediaContentType0": "image/jpeg",
                "MessageSid": "SM456",
            },
        )
        assert resp.status_code == 200
        mock_process.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_webhook.py::TestWebhookEndpoint -v`
Expected: FAIL — cannot import `create_app`

**Step 3: Write minimal implementation**

```python
# src/webhook/main.py
from __future__ import annotations

import logging

from flask import Flask, request, Response

from webhook.twilio_handler import parse_twilio_request

logger = logging.getLogger(__name__)


def process_incoming_message(twilio_msg, form_data):
    """Process an incoming message. Stubbed — will be wired to GCS/Firestore later."""
    logger.info(
        "Received message from %s: %s (media: %d)",
        twilio_msg.sender,
        twilio_msg.body[:50] if twilio_msg.body else "(no text)",
        len(twilio_msg.media_urls),
    )


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/webhook/sms")
    def incoming_sms():
        twilio_msg = parse_twilio_request(request.form)
        process_incoming_message(twilio_msg, request.form)

        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Got it!</Message></Response>'
        return Response(twiml, content_type="application/xml")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_webhook.py -v`
Expected: All PASS

**Step 5: Create Dockerfile and requirements.txt**

```dockerfile
# src/webhook/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY src/webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/shared/ /app/shared/
COPY src/webhook/ /app/webhook/

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "30", "webhook.main:create_app()"]
```

```
# src/webhook/requirements.txt
flask>=3.0
twilio>=9.0
google-cloud-storage>=2.14
google-cloud-firestore>=2.16
gunicorn>=22.0
python-dotenv>=1.0
```

**Step 6: Commit**

```bash
git add src/webhook/main.py src/webhook/Dockerfile src/webhook/requirements.txt tests/test_webhook.py
git commit -m "feat: add webhook Flask app with health check and SMS endpoint"
```

---

## Phase 3: Batch Processor

### Task 6: EXIF extraction

**Files:**
- Create: `src/batch/exif.py`
- Create: `tests/test_exif.py`
- Create: `tests/fixtures/` (we'll create a minimal JPEG with EXIF for testing)

**Step 1: Write the failing tests**

```python
# tests/test_exif.py
import pytest
from datetime import datetime
from pathlib import Path
from batch.exif import extract_exif


class TestExtractExif:
    def test_extract_from_jpeg_with_gps(self, sample_photo_with_exif):
        """Test against a real JPEG with EXIF data."""
        result = extract_exif(sample_photo_with_exif)
        assert result is not None
        assert "timestamp" in result or "gps" in result or result == {}

    def test_extract_from_bytes_without_exif(self):
        """A minimal JPEG with no EXIF returns empty dict."""
        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), "red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        result = extract_exif(buf.read())
        assert result == {}

    def test_extract_returns_timestamp_when_present(self, jpeg_with_timestamp):
        result = extract_exif(jpeg_with_timestamp)
        assert "timestamp" in result
        # Should be a datetime object
        assert isinstance(result["timestamp"], datetime)

    def test_extract_returns_gps_when_present(self, jpeg_with_gps):
        result = extract_exif(jpeg_with_gps)
        assert "gps" in result
        assert "lat" in result["gps"]
        assert "lng" in result["gps"]
```

Add to `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
import io
import struct
from PIL import Image
from PIL.ExifTags import Base as ExifBase
from pathlib import Path


@pytest.fixture
def sample_photo_with_exif():
    """Create a minimal JPEG with basic EXIF data."""
    img = Image.new("RGB", (100, 100), "blue")
    exif = img.getexif()
    exif[ExifBase.DateTime] = "2026:05:22 14:30:00"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


@pytest.fixture
def jpeg_with_timestamp():
    """JPEG with EXIF DateTime."""
    img = Image.new("RGB", (100, 100), "green")
    exif = img.getexif()
    exif[ExifBase.DateTime] = "2026:05:22 14:30:00"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


@pytest.fixture
def jpeg_with_gps():
    """JPEG with EXIF GPS data. Uses IFD approach for GPS tags."""
    img = Image.new("RGB", (100, 100), "green")
    exif = img.getexif()

    # GPS IFD (tag 0x8825)
    from PIL.ExifTags import IFD, GPS

    gps_ifd = {
        GPS.GPSLatitudeRef: "N",
        GPS.GPSLatitude: (51.0, 30.0, 26.64),
        GPS.GPSLongitudeRef: "W",
        GPS.GPSLongitude: (0.0, 6.0, 56.52),
    }
    exif[ExifBase.GPSInfo] = gps_ifd

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_exif.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'batch.exif'`

**Step 3: Write minimal implementation**

```python
# src/batch/exif.py
from __future__ import annotations

import io
from datetime import datetime

from PIL import Image
from PIL.ExifTags import Base as ExifBase, GPS


def extract_exif(image_data: bytes) -> dict:
    """Extract EXIF metadata from JPEG image bytes.

    Returns dict with optional keys: timestamp (datetime), gps ({lat, lng}), device (str).
    Returns empty dict if no EXIF data found.
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        exif = img.getexif()
    except Exception:
        return {}

    if not exif:
        return {}

    result = {}

    # Timestamp
    dt_str = exif.get(ExifBase.DateTime) or exif.get(ExifBase.DateTimeOriginal)
    if dt_str:
        try:
            result["timestamp"] = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass

    # GPS
    gps_info = exif.get(ExifBase.GPSInfo)
    if isinstance(gps_info, dict):
        try:
            lat = _dms_to_decimal(
                gps_info.get(GPS.GPSLatitude),
                gps_info.get(GPS.GPSLatitudeRef),
            )
            lng = _dms_to_decimal(
                gps_info.get(GPS.GPSLongitude),
                gps_info.get(GPS.GPSLongitudeRef),
            )
            if lat is not None and lng is not None:
                result["gps"] = {"lat": lat, "lng": lng}
        except (TypeError, ValueError):
            pass

    # Device
    make = exif.get(ExifBase.Make, "")
    model = exif.get(ExifBase.Model, "")
    if make or model:
        result["device"] = f"{make} {model}".strip()

    return result


def _dms_to_decimal(dms: tuple | None, ref: str | None) -> float | None:
    """Convert (degrees, minutes, seconds) + N/S/E/W ref to decimal degrees."""
    if dms is None or ref is None:
        return None
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_exif.py -v`
Expected: All PASS (GPS test may need fixture adjustment — verify and fix)

**Step 5: Commit**

```bash
git add src/batch/__init__.py src/batch/exif.py tests/test_exif.py tests/conftest.py
git commit -m "feat: add EXIF extraction (timestamp, GPS, device)"
```

---

### Task 7: Image resizing

**Files:**
- Create: `src/batch/resize.py`
- Create: `tests/test_resize.py`

**Step 1: Write the failing tests**

```python
# tests/test_resize.py
import io
import pytest
from PIL import Image
from batch.resize import resize_image


class TestResizeImage:
    def _make_jpeg(self, width: int, height: int) -> bytes:
        img = Image.new("RGB", (width, height), "blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_resize_large(self):
        original = self._make_jpeg(4000, 3000)
        result = resize_image(original, max_dimension=1600)
        img = Image.open(io.BytesIO(result))
        assert max(img.size) == 1600
        assert img.size == (1600, 1200)

    def test_resize_thumb(self):
        original = self._make_jpeg(4000, 3000)
        result = resize_image(original, max_dimension=400)
        img = Image.open(io.BytesIO(result))
        assert max(img.size) == 400

    def test_no_upscale(self):
        """Images smaller than max_dimension should not be upscaled."""
        original = self._make_jpeg(300, 200)
        result = resize_image(original, max_dimension=1600)
        img = Image.open(io.BytesIO(result))
        assert img.size == (300, 200)

    def test_portrait_orientation(self):
        original = self._make_jpeg(3000, 4000)
        result = resize_image(original, max_dimension=1600)
        img = Image.open(io.BytesIO(result))
        assert max(img.size) == 1600
        assert img.size == (1200, 1600)

    def test_output_is_jpeg(self):
        original = self._make_jpeg(2000, 1500)
        result = resize_image(original, max_dimension=1600)
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_resize.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/batch/resize.py
from __future__ import annotations

import io

from PIL import Image


def resize_image(image_data: bytes, max_dimension: int = 1600) -> bytes:
    """Resize an image so its longest side is at most max_dimension pixels.

    Does not upscale. Returns JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_data))

    # Don't upscale
    if max(img.size) <= max_dimension:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    # Calculate new size preserving aspect ratio
    ratio = max_dimension / max(img.size)
    new_size = (int(img.width * ratio), int(img.height * ratio))

    img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_resize.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/batch/resize.py tests/test_resize.py
git commit -m "feat: add image resizing with aspect ratio preservation"
```

---

### Task 8: Near-duplicate detection

**Files:**
- Create: `src/batch/dedup.py`
- Create: `tests/test_dedup.py`

**Step 1: Write the failing tests**

```python
# tests/test_dedup.py
import io
import pytest
from PIL import Image
from batch.dedup import compute_hash, find_duplicates


class TestComputeHash:
    def _make_image_bytes(self, color: str, size=(100, 100)) -> bytes:
        img = Image.new("RGB", size, color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_same_image_same_hash(self):
        data = self._make_image_bytes("red")
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        assert h1 == h2

    def test_different_images_different_hash(self):
        h1 = compute_hash(self._make_image_bytes("red"))
        h2 = compute_hash(self._make_image_bytes("blue"))
        assert h1 != h2

    def test_slightly_resized_images_similar_hash(self):
        """Images that are very similar should have similar hashes (low hamming distance)."""
        img = Image.new("RGB", (200, 200), "red")
        buf1 = io.BytesIO()
        img.save(buf1, format="JPEG", quality=95)

        buf2 = io.BytesIO()
        img.save(buf2, format="JPEG", quality=50)

        h1 = compute_hash(buf1.getvalue())
        h2 = compute_hash(buf2.getvalue())
        # Same image at different quality — hashes should be identical or very close
        assert h1 == h2


class TestFindDuplicates:
    def _make_image_bytes(self, color: str) -> bytes:
        img = Image.new("RGB", (100, 100), color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_no_duplicates(self):
        items = [
            {"id": "a", "image_data": self._make_image_bytes("red")},
            {"id": "b", "image_data": self._make_image_bytes("blue")},
            {"id": "c", "image_data": self._make_image_bytes("green")},
        ]
        dupes = find_duplicates(items)
        assert dupes == set()

    def test_finds_exact_duplicates(self):
        red = self._make_image_bytes("red")
        items = [
            {"id": "a", "image_data": red, "quality": 8},
            {"id": "b", "image_data": red, "quality": 5},
            {"id": "c", "image_data": self._make_image_bytes("blue"), "quality": 7},
        ]
        dupes = find_duplicates(items)
        # Should mark the lower-quality duplicate for removal
        assert "b" in dupes
        assert "a" not in dupes
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dedup.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/batch/dedup.py
from __future__ import annotations

import io

from PIL import Image


def compute_hash(image_data: bytes, hash_size: int = 8) -> int:
    """Compute a perceptual hash (average hash) of an image.

    Returns an integer representing the hash.
    """
    img = Image.open(io.BytesIO(image_data)).convert("L")
    img = img.resize((hash_size, hash_size), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    return sum(1 << i for i, px in enumerate(pixels) if px >= avg)


def hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    return bin(h1 ^ h2).count("1")


def find_duplicates(
    items: list[dict],
    threshold: int = 5,
) -> set[str]:
    """Find near-duplicate images and return IDs to remove.

    Each item must have 'id', 'image_data', and optionally 'quality'.
    When duplicates are found, keeps the one with the highest quality score.

    Returns set of item IDs that should be removed.
    """
    hashes = []
    for item in items:
        h = compute_hash(item["image_data"])
        hashes.append((item["id"], h, item.get("quality", 0)))

    to_remove = set()
    for i in range(len(hashes)):
        if hashes[i][0] in to_remove:
            continue
        for j in range(i + 1, len(hashes)):
            if hashes[j][0] in to_remove:
                continue
            dist = hamming_distance(hashes[i][1], hashes[j][1])
            if dist <= threshold:
                # Keep the higher quality one
                if hashes[i][2] >= hashes[j][2]:
                    to_remove.add(hashes[j][0])
                else:
                    to_remove.add(hashes[i][0])

    return to_remove
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dedup.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/batch/dedup.py tests/test_dedup.py
git commit -m "feat: add perceptual hashing and near-duplicate detection"
```

---

### Task 9: Claude vision analysis

**Files:**
- Create: `src/batch/analyze.py`
- Create: `tests/test_analyze.py`

**Step 1: Write the failing tests**

```python
# tests/test_analyze.py
import pytest
import json
from unittest.mock import patch, MagicMock
from batch.analyze import analyze_photo, analyze_text_message, build_photo_prompt


class TestBuildPhotoPrompt:
    def test_includes_trip_context(self):
        prompt = build_photo_prompt(
            day_number=2,
            destination="London & Cornwall",
            planned_locations=["Borough Market", "Shakespeare's Globe"],
            time="14:30",
            location="South Bank",
            sender_name="Kevin",
        )
        assert "Day 2" in prompt
        assert "London & Cornwall" in prompt
        assert "Borough Market" in prompt
        assert "Kevin" in prompt
        assert "14:30" in prompt


class TestAnalyzePhoto:
    @patch("batch.analyze.get_anthropic_client")
    def test_returns_expected_fields(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "caption": "A beautiful view from the Globe Theatre.",
                    "category": "sightseeing",
                    "quality": 8,
                    "alt": "View from the Globe Theatre over the Thames",
                })
            )
        ]
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyze_photo(
            image_data=b"fake-image-data",
            day_number=2,
            destination="London",
            planned_locations=["Globe Theatre"],
            time="14:30",
            location="South Bank",
            sender_name="Kevin",
        )
        assert result["caption"] == "A beautiful view from the Globe Theatre."
        assert result["category"] == "sightseeing"
        assert result["quality"] == 8
        assert "alt" in result


class TestAnalyzeTextMessage:
    @patch("batch.analyze.get_anthropic_client")
    def test_classifies_text_message(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"type": "quote"}))
        ]
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyze_text_message("This cream tea is incredible")
        assert result["type"] == "quote"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_analyze.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/batch/analyze.py
from __future__ import annotations

import base64
import json
import logging

import anthropic

logger = logging.getLogger(__name__)

_client = None


def get_anthropic_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def build_photo_prompt(
    day_number: int,
    destination: str,
    planned_locations: list[str],
    time: str,
    location: str,
    sender_name: str,
) -> str:
    locations_str = ", ".join(planned_locations) if planned_locations else "various locations"
    return f"""This is a photo from Day {day_number} of a trip to {destination}.
Today's planned locations: {locations_str}.
The photo was taken at {time} near {location}.
It was sent by {sender_name}.

Please provide a JSON object with exactly these fields:
1. "caption": A natural, warm caption (1-2 sentences)
2. "category": One of: sightseeing, food, sports, nature, group, transport, nightlife
3. "quality": Score 1-10 (composition, sharpness, visual interest)
4. "alt": Brief description for accessibility (alt text)

Respond with ONLY the JSON object, no other text."""


def analyze_photo(
    image_data: bytes,
    day_number: int,
    destination: str,
    planned_locations: list[str],
    time: str,
    location: str,
    sender_name: str,
) -> dict:
    """Analyze a photo using Claude vision API.

    Returns dict with: caption, category, quality, alt.
    """
    client = get_anthropic_client()
    prompt = build_photo_prompt(
        day_number=day_number,
        destination=destination,
        planned_locations=planned_locations,
        time=time,
        location=location,
        sender_name=sender_name,
    )

    b64_image = base64.b64encode(image_data).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    return json.loads(response.content[0].text)


def analyze_text_message(text: str) -> dict:
    """Classify a text-only message.

    Returns dict with: type (one of: quote, reaction, story).
    """
    client = get_anthropic_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": f"""Classify this text message from a trip participant into one category.

Message: "{text}"

Respond with ONLY a JSON object: {{"type": "quote"|"reaction"|"story"}}""",
            }
        ],
    )

    return json.loads(response.content[0].text)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_analyze.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/batch/analyze.py tests/test_analyze.py
git commit -m "feat: add Claude vision photo analysis and text classification"
```

---

### Task 10: Journal curation logic

**Files:**
- Create: `src/batch/curate.py`
- Create: `tests/test_curate.py`

**Step 1: Write the failing tests**

```python
# tests/test_curate.py
import pytest
from batch.curate import (
    group_by_day,
    cluster_by_time,
    select_journal_photos,
    select_hero_photo,
    arrange_chronologically,
)


def _photo(time: str, quality: int, category: str = "sightseeing", by: str = "Kevin"):
    return {
        "type": "photo",
        "url": f"processed/large/{time.replace(':', '')}.jpg",
        "thumb": f"processed/thumb/{time.replace(':', '')}.jpg",
        "caption": f"Photo at {time}",
        "alt": f"Photo at {time}",
        "by": by,
        "time": time,
        "location": "London",
        "category": category,
        "quality": quality,
    }


def _quote(time: str, by: str = "Kevin"):
    return {
        "type": "quote",
        "text": f"Message at {time}",
        "by": by,
        "time": time,
    }


class TestGroupByDay:
    def test_groups_items_by_day_number(self):
        items = [
            {"day": 1, **_photo("09:00", 7)},
            {"day": 1, **_photo("14:00", 8)},
            {"day": 2, **_photo("10:00", 6)},
        ]
        grouped = group_by_day(items)
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1

    def test_empty_input(self):
        assert group_by_day([]) == {}


class TestClusterByTime:
    def test_clusters_close_times(self):
        items = [
            _photo("09:00", 7),
            _photo("09:15", 6),
            _photo("09:20", 8),
            _photo("14:00", 5),
            _photo("14:10", 7),
        ]
        clusters = cluster_by_time(items, gap_minutes=60)
        assert len(clusters) == 2
        assert len(clusters[0]) == 3
        assert len(clusters[1]) == 2


class TestSelectJournalPhotos:
    def test_selects_top_photos_per_cluster(self):
        cluster = [
            _photo("09:00", 5),
            _photo("09:15", 9),
            _photo("09:20", 7),
            _photo("09:25", 3),
            _photo("09:30", 8, category="food"),
        ]
        selected = select_journal_photos(cluster, max_per_cluster=3)
        assert len(selected) == 3
        # Should include the highest quality photos
        qualities = [p["quality"] for p in selected]
        assert 9 in qualities
        assert 8 in qualities

    def test_prioritizes_variety_in_category(self):
        cluster = [
            _photo("09:00", 9, category="sightseeing"),
            _photo("09:15", 8, category="sightseeing"),
            _photo("09:20", 7, category="food"),
            _photo("09:25", 6, category="group"),
        ]
        selected = select_journal_photos(cluster, max_per_cluster=3)
        categories = [p["category"] for p in selected]
        # Should have variety — not all sightseeing
        assert len(set(categories)) >= 2


class TestSelectHeroPhoto:
    def test_selects_highest_quality(self):
        photos = [
            _photo("09:00", 5),
            _photo("10:00", 9),
            _photo("14:00", 7),
        ]
        hero = select_hero_photo(photos)
        assert hero["quality"] == 9

    def test_empty_list_returns_none(self):
        assert select_hero_photo([]) is None


class TestArrangeChronologically:
    def test_sorts_by_time(self):
        items = [
            _photo("14:00", 7),
            _quote("10:30"),
            _photo("09:00", 8),
        ]
        arranged = arrange_chronologically(items)
        times = [i["time"] for i in arranged]
        assert times == ["09:00", "10:30", "14:00"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_curate.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/batch/curate.py
from __future__ import annotations

from collections import defaultdict


def group_by_day(items: list[dict]) -> dict[int, list[dict]]:
    """Group items by their 'day' field."""
    grouped: dict[int, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["day"]].append(item)
    return dict(grouped)


def _time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def cluster_by_time(items: list[dict], gap_minutes: int = 60) -> list[list[dict]]:
    """Cluster items by time proximity. Items within gap_minutes of each other are in the same cluster."""
    if not items:
        return []

    sorted_items = sorted(items, key=lambda x: x["time"])
    clusters: list[list[dict]] = [[sorted_items[0]]]

    for item in sorted_items[1:]:
        prev_time = _time_to_minutes(clusters[-1][-1]["time"])
        curr_time = _time_to_minutes(item["time"])
        if curr_time - prev_time <= gap_minutes:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    return clusters


def select_journal_photos(
    cluster: list[dict],
    max_per_cluster: int = 3,
) -> list[dict]:
    """Select top photos from a cluster, prioritizing quality and category variety."""
    photos = [item for item in cluster if item.get("type") == "photo"]
    if not photos:
        return []

    if len(photos) <= max_per_cluster:
        return photos

    # Sort by quality descending
    by_quality = sorted(photos, key=lambda p: p["quality"], reverse=True)

    selected = [by_quality[0]]
    seen_categories = {by_quality[0]["category"]}

    # Second pass: prefer different categories
    for photo in by_quality[1:]:
        if len(selected) >= max_per_cluster:
            break
        if photo["category"] not in seen_categories:
            selected.append(photo)
            seen_categories.add(photo["category"])

    # Fill remaining slots with highest quality
    for photo in by_quality[1:]:
        if len(selected) >= max_per_cluster:
            break
        if photo not in selected:
            selected.append(photo)

    return selected


def select_hero_photo(photos: list[dict]) -> dict | None:
    """Select the single best photo (highest quality)."""
    if not photos:
        return None
    return max(photos, key=lambda p: p.get("quality", 0))


def arrange_chronologically(items: list[dict]) -> list[dict]:
    """Sort items by their 'time' field."""
    return sorted(items, key=lambda x: x.get("time", ""))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_curate.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/batch/curate.py tests/test_curate.py
git commit -m "feat: add journal curation logic (grouping, clustering, selection)"
```

---

### Task 11: Manifest builder

**Files:**
- Create: `src/batch/manifest.py`
- Create: `tests/test_manifest.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
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
    """Build a single day's entry for the manifest."""
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
    """Build the complete manifest.json structure."""
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/batch/manifest.py tests/test_manifest.py
git commit -m "feat: add manifest builder for frontend consumption"
```

---

## Phase 4: Frontend

### Task 12: Frontend memories.js component

**Files:**
- Create: `frontend/memories.js`
- Create: `frontend/memories.css`
- Create: `frontend/lightbox.js`

This task is frontend-only — no unit tests (vanilla JS, tested via browser). Implementation is guided directly by the design doc.

**Step 1: Create memories.css**

Style the journal view and scrapbook view, consistent with the invitation's existing design language (navy, gold, cream palette, Cormorant Garamond + Inter fonts).

Key CSS classes:
- `.memories-nav` — toggle between journal/scrapbook
- `.journal-day` — day card in journal view
- `.journal-hero` — hero photo
- `.journal-supporting` — supporting photo row
- `.journal-summary` — AI day summary
- `.journal-quote` — pull-quote from text messages
- `.scrapbook-grid` — masonry grid
- `.scrapbook-filters` — filter chips
- `.scrapbook-photo` — individual photo card

**Step 2: Create memories.js**

Core logic:
- `Memories.init(containerId, manifestUrl)` — entry point
- Fetches `manifest.json`, determines phase (pre/during/post), renders appropriate view
- Journal view: iterate `manifest.days`, render hero + supporting + summary + quotes
- Scrapbook view: flatten all scrapbook items, render grid with filter chips
- Filter by day, person, location

**Step 3: Create lightbox.js**

- Click any photo → full-screen lightbox overlay
- Shows: large image, caption, who/when/where
- Arrow keys / swipe to navigate within the current view
- Escape / click outside to close

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend memories component (journal, scrapbook, lightbox)"
```

---

## Phase 5: GCS + Firestore Wiring

### Task 13: GCS helper utilities

**Files:**
- Create: `src/shared/gcs.py`
- Create: `tests/test_gcs.py`

**Step 1: Write the failing tests**

```python
# tests/test_gcs.py
import pytest
from unittest.mock import patch, MagicMock
from shared.gcs import upload_blob, download_blob, build_raw_path, build_processed_path


class TestPathBuilders:
    def test_build_raw_path(self):
        path = build_raw_path("uk-2026", "20260522_143022", "kevin", ".jpg")
        assert path == "uk-2026/raw/20260522_143022_kevin.jpg"

    def test_build_processed_path_large(self):
        path = build_processed_path("uk-2026", "20260522_143022_kevin.jpg", "large")
        assert path == "uk-2026/processed/large/20260522_143022_kevin.jpg"

    def test_build_processed_path_thumb(self):
        path = build_processed_path("uk-2026", "20260522_143022_kevin.jpg", "thumb")
        assert path == "uk-2026/processed/thumb/20260522_143022_kevin.jpg"


class TestUploadBlob:
    @patch("shared.gcs.get_bucket")
    def test_uploads_bytes(self, mock_get_bucket):
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_get_bucket.return_value = mock_bucket

        upload_blob("uk-2026/raw/photo.jpg", b"image-data", "image/jpeg")

        mock_bucket.blob.assert_called_once_with("uk-2026/raw/photo.jpg")
        mock_blob.upload_from_string.assert_called_once_with(b"image-data", content_type="image/jpeg")


class TestDownloadBlob:
    @patch("shared.gcs.get_bucket")
    def test_downloads_bytes(self, mock_get_bucket):
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = b"image-data"
        mock_bucket.blob.return_value = mock_blob
        mock_get_bucket.return_value = mock_bucket

        result = download_blob("uk-2026/raw/photo.jpg")
        assert result == b"image-data"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_gcs.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/shared/gcs.py
from __future__ import annotations

import os

from google.cloud import storage

_bucket = None


def get_bucket() -> storage.Bucket:
    global _bucket
    if _bucket is None:
        client = storage.Client()
        bucket_name = os.environ["GCS_BUCKET_NAME"]
        _bucket = client.bucket(bucket_name)
    return _bucket


def upload_blob(path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload bytes to a GCS path."""
    blob = get_bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)


def download_blob(path: str) -> bytes:
    """Download bytes from a GCS path."""
    blob = get_bucket().blob(path)
    return blob.download_as_bytes()


def build_raw_path(trip_id: str, timestamp: str, sender: str, ext: str) -> str:
    """Build the GCS path for a raw photo."""
    return f"{trip_id}/raw/{timestamp}_{sender}{ext}"


def build_processed_path(trip_id: str, filename: str, size: str) -> str:
    """Build the GCS path for a processed photo (size: 'large' or 'thumb')."""
    return f"{trip_id}/processed/{size}/{filename}"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_gcs.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/shared/gcs.py tests/test_gcs.py
git commit -m "feat: add GCS helper utilities"
```

---

### Task 14: Firestore helpers

**Files:**
- Create: `src/shared/firestore.py`
- Create: `tests/test_firestore.py`

**Step 1: Write the failing tests**

```python
# tests/test_firestore.py
import pytest
from unittest.mock import patch, MagicMock
from shared.firestore import (
    save_message,
    get_unprocessed_messages,
    mark_message_processed,
    get_trip_config_doc,
)
from shared.models import Message
from datetime import datetime


class TestSaveMessage:
    @patch("shared.firestore.get_db")
    def test_saves_to_correct_collection(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_collection

        msg = Message(
            id="",
            trip_id="uk-2026",
            sender_phone="+15551234567",
            sender_name="Kevin",
            timestamp=datetime(2026, 5, 22, 14, 30),
            text="Hello!",
            media_urls=[],
            processed=False,
        )
        save_message(msg)
        mock_collection.add.assert_called_once()


class TestGetUnprocessedMessages:
    @patch("shared.firestore.get_db")
    def test_queries_unprocessed(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_doc = MagicMock()
        mock_doc.id = "msg-1"
        mock_doc.to_dict.return_value = {
            "trip_id": "uk-2026",
            "sender_phone": "+15551234567",
            "sender_name": "Kevin",
            "timestamp": "2026-05-22T14:30:00",
            "text": "Hello",
            "media_urls": [],
            "processed": False,
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value.where.return_value = mock_query

        messages = get_unprocessed_messages("uk-2026")
        assert len(messages) == 1
        assert messages[0].sender_name == "Kevin"


class TestMarkMessageProcessed:
    @patch("shared.firestore.get_db")
    def test_updates_processed_flag(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref

        mark_message_processed("uk-2026", "msg-1")
        mock_doc_ref.update.assert_called_once_with({"processed": True})
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_firestore.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/shared/firestore.py
from __future__ import annotations

from google.cloud import firestore

from shared.models import Message

_db = None


def get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def save_message(msg: Message) -> str:
    """Save an incoming message to Firestore. Returns the document ID."""
    db = get_db()
    collection = db.collection("trips").document(msg.trip_id).collection("messages")
    _, doc_ref = collection.add(msg.to_dict())
    return doc_ref.id


def get_unprocessed_messages(trip_id: str) -> list[Message]:
    """Get all unprocessed messages for a trip."""
    db = get_db()
    collection = db.collection("trips").document(trip_id).collection("messages")
    query = collection.where("processed", "==", False)

    messages = []
    for doc in query.stream():
        messages.append(Message.from_dict(doc.id, doc.to_dict()))
    return messages


def mark_message_processed(trip_id: str, message_id: str) -> None:
    """Mark a message as processed in Firestore."""
    db = get_db()
    doc_ref = db.collection("trips").document(trip_id).collection("messages").document(message_id)
    doc_ref.update({"processed": True})


def get_trip_config_doc(trip_id: str) -> dict | None:
    """Get trip configuration from Firestore."""
    db = get_db()
    doc = db.collection("trips").document(trip_id).get()
    if doc.exists:
        return doc.to_dict()
    return None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_firestore.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/shared/firestore.py tests/test_firestore.py
git commit -m "feat: add Firestore helpers for message CRUD"
```

---

### Task 15: Wire webhook to GCS + Firestore

**Files:**
- Modify: `src/webhook/main.py`
- Modify: `src/webhook/twilio_handler.py` (add sender validation)
- Create: `src/webhook/storage.py`
- Modify: `tests/test_webhook.py` (add integration-style tests)

**Step 1: Write failing tests for sender validation**

```python
# Add to tests/test_webhook.py
from webhook.twilio_handler import validate_sender
from shared.models import TripConfig


class TestValidateSender:
    def test_known_sender_returns_participant(self):
        config = TripConfig.from_dict({
            "id": "test", "title": "Test", "destination": "Test",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "UTC", "locations": [],
            "participants": [{"name": "Kevin", "phone": "+15551234567"}],
        })
        result = validate_sender("+15551234567", config)
        assert result is not None
        assert result.name == "Kevin"

    def test_unknown_sender_returns_none(self):
        config = TripConfig.from_dict({
            "id": "test", "title": "Test", "destination": "Test",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "UTC", "locations": [],
            "participants": [{"name": "Kevin", "phone": "+15551234567"}],
        })
        result = validate_sender("+19999999999", config)
        assert result is None
```

**Step 2: Implement sender validation**

Add to `src/webhook/twilio_handler.py`:

```python
from shared.models import TripConfig, Participant

def validate_sender(phone: str, config: TripConfig) -> Participant | None:
    """Validate that a phone number belongs to a registered participant."""
    return config.find_participant(phone)
```

**Step 3: Create webhook storage helper**

```python
# src/webhook/storage.py
from __future__ import annotations

import logging
import requests

from shared.gcs import upload_blob, build_raw_path

logger = logging.getLogger(__name__)


def download_and_store_media(
    trip_id: str,
    media_url: str,
    content_type: str,
    timestamp: str,
    sender_name: str,
    index: int = 0,
) -> str:
    """Download media from Twilio and store in GCS. Returns the GCS path."""
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif"}
    ext = ext_map.get(content_type, ".jpg")
    filename_base = f"{timestamp}_{index}" if index > 0 else timestamp

    gcs_path = build_raw_path(trip_id, filename_base, sender_name.lower(), ext)

    response = requests.get(media_url)
    response.raise_for_status()

    upload_blob(gcs_path, response.content, content_type)
    logger.info("Stored media at %s", gcs_path)
    return gcs_path
```

**Step 4: Wire into main.py (update process_incoming_message)**

Update `src/webhook/main.py` to call the real storage/Firestore when not in testing mode.

**Step 5: Run all webhook tests**

Run: `uv run pytest tests/test_webhook.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/webhook/ tests/test_webhook.py
git commit -m "feat: wire webhook to GCS storage and Firestore, add sender validation"
```

---

### Task 16: Batch processor main entry point

**Files:**
- Create: `src/batch/main.py`
- Create: `src/batch/Dockerfile`
- Create: `src/batch/requirements.txt`

This task wires together all the batch components (exif, resize, analyze, curate, manifest, dedup) into the nightly pipeline. Tests are primarily for the orchestration logic.

**Step 1: Write tests for the batch orchestration**

```python
# tests/test_batch.py
import pytest
from unittest.mock import patch, MagicMock
from batch.main import process_trip_batch


class TestProcessTripBatch:
    @patch("batch.main.get_unprocessed_messages")
    @patch("batch.main.download_blob")
    @patch("batch.main.upload_blob")
    @patch("batch.main.extract_exif")
    @patch("batch.main.resize_image")
    @patch("batch.main.analyze_photo")
    @patch("batch.main.mark_message_processed")
    @patch("batch.main.load_trip_config")
    def test_processes_unprocessed_messages(
        self, mock_load_config, mock_mark, mock_analyze, mock_resize,
        mock_exif, mock_upload, mock_download, mock_get_msgs,
    ):
        # Setup: return one unprocessed message with one photo
        from shared.models import Message, TripConfig
        from datetime import datetime

        mock_load_config.return_value = TripConfig.from_dict({
            "id": "uk-2026", "title": "England 2026", "destination": "London",
            "dates": {"start": "2026-05-21", "end": "2026-05-28"},
            "timezone": "Europe/London", "locations": [],
            "participants": [{"name": "Kevin", "phone": "+15551234567"}],
        })

        mock_get_msgs.return_value = [
            Message(
                id="msg-1", trip_id="uk-2026", sender_phone="+15551234567",
                sender_name="Kevin", timestamp=datetime(2026, 5, 22, 14, 30),
                text="Cool view!", media_urls=["uk-2026/raw/photo.jpg"],
                processed=False,
            )
        ]
        mock_download.return_value = b"fake-image"
        mock_exif.return_value = {}
        mock_resize.return_value = b"resized-image"
        mock_analyze.return_value = {
            "caption": "A view", "category": "sightseeing",
            "quality": 7, "alt": "A nice view",
        }

        # Should not raise
        process_trip_batch("uk-2026", dry_run=True)

        mock_get_msgs.assert_called_once_with("uk-2026")
        assert mock_download.called
        assert mock_resize.called
```

**Step 2: Implement batch main.py**

The full orchestration: fetch unprocessed messages → for each photo: download, extract EXIF, resize, analyze → curate journal → build manifest → upload manifest → mark processed.

**Step 3: Create Dockerfile and requirements.txt for batch**

**Step 4: Run tests**

Run: `uv run pytest tests/test_batch.py -v`

**Step 5: Commit**

```bash
git add src/batch/main.py src/batch/Dockerfile src/batch/requirements.txt tests/test_batch.py
git commit -m "feat: add batch processor orchestration"
```

---

## Phase 6: Terraform Infrastructure

### Task 17: Terraform base setup

**Files:**
- Create: `terraform/main.tf`
- Create: `terraform/variables.tf`
- Create: `terraform/outputs.tf`
- Create: `terraform/terraform.tfvars.example`

No tests (Terraform validation via `terraform validate`).

**Step 1: Create terraform/main.tf, variables.tf, outputs.tf**

Provider config for Google Cloud, backend config (GCS state bucket), project-level settings.

**Step 2: Create terraform.tfvars.example**

**Step 3: Validate**

Run: `cd terraform && terraform init && terraform validate`
Expected: "Success! The configuration is valid."

**Step 4: Commit**

```bash
git add terraform/main.tf terraform/variables.tf terraform/outputs.tf terraform/terraform.tfvars.example
git commit -m "chore: add Terraform base config (provider, variables, outputs)"
```

---

### Task 18: Terraform resources (GCS, Firestore, Cloud Run, Scheduler, IAM, Secrets)

**Files:**
- Create: `terraform/storage.tf`
- Create: `terraform/firestore.tf`
- Create: `terraform/cloud_run.tf`
- Create: `terraform/scheduler.tf`
- Create: `terraform/iam.tf`
- Create: `terraform/secrets.tf`
- Create: `terraform/environments/dev.tfvars` (example only)
- Create: `terraform/environments/prod.tfvars` (example only)

**Step 1: Create each .tf file per the design doc**

- `storage.tf`: GCS bucket `memoria-{project-id}`
- `firestore.tf`: Firestore database + indexes
- `cloud_run.tf`: Webhook service + batch job
- `scheduler.tf`: Cloud Scheduler for nightly batch
- `iam.tf`: Service accounts + least-privilege bindings
- `secrets.tf`: Secret Manager for Twilio + Claude API keys

**Step 2: Create environment tfvars**

**Step 3: Validate**

Run: `cd terraform && terraform validate`
Expected: Valid

**Step 4: Commit**

```bash
git add terraform/
git commit -m "feat: add Terraform resources (GCS, Firestore, Cloud Run, Scheduler, IAM, Secrets)"
```

---

## Phase 7: Scripts & CLI Tools

### Task 19: CLI scripts

**Files:**
- Create: `scripts/create_trip.py`
- Create: `scripts/register_participant.py`
- Create: `scripts/run_batch.py`
- Create: `scripts/export_trip.py`

These are thin CLI wrappers around the library code. Light testing via mocks.

**Step 1: Create scripts**

- `create_trip.py`: Load YAML → write to Firestore
- `register_participant.py`: Add participant to trip in Firestore
- `run_batch.py`: Manually trigger batch processing
- `export_trip.py`: Download from GCS, build static bundle

**Step 2: Commit**

```bash
git add scripts/
git commit -m "feat: add CLI scripts for trip management"
```

---

## Phase 8: Export & Keepsake

### Task 20: Static export tool

**Files:**
- Create: `src/export/export.py`
- Create: `src/export/templates/keepsake.html`
- Create: `tests/test_export.py`

**Step 1: Write the failing tests**

```python
# tests/test_export.py
import pytest
import json
from pathlib import Path
from batch.manifest import build_manifest, build_day_entry
from shared.models import TripConfig
from export.export import rewrite_manifest_urls, build_keepsake_html


class TestRewriteManifestUrls:
    def test_rewrites_gcs_urls_to_relative(self):
        manifest = {
            "trip": {"id": "uk-2026", "title": "Test", "dates": {"start": "2026-05-21", "end": "2026-05-28"}, "participants": []},
            "days": [{
                "date": "2026-05-22",
                "dayNumber": 2,
                "label": "Day 2",
                "title": "Test",
                "summary": "A day.",
                "journal": [{
                    "type": "photo",
                    "url": "processed/large/photo.jpg",
                    "thumb": "processed/thumb/photo.jpg",
                    "caption": "Test",
                    "alt": "Test",
                    "by": "Kevin",
                    "time": "14:30",
                    "location": "London",
                    "category": "sightseeing",
                    "quality": 7,
                }],
                "scrapbook": [],
            }],
        }
        rewritten = rewrite_manifest_urls(manifest)
        assert rewritten["days"][0]["journal"][0]["url"] == "assets/large/photo.jpg"
        assert rewritten["days"][0]["journal"][0]["thumb"] == "assets/thumb/photo.jpg"
```

**Step 2: Implement export.py**

**Step 3: Run tests and commit**

```bash
git add src/export/ tests/test_export.py
git commit -m "feat: add static export tool for keepsake bundles"
```

---

## Phase 9: CI & Test Fixtures

### Task 21: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

Lint (ruff), test (pytest), Terraform validate.

**Step 1: Create CI workflow**

**Step 2: Commit**

```bash
git add .github/
git commit -m "chore: add GitHub Actions CI (lint, test, terraform validate)"
```

---

### Task 22: Synthetic test fixtures

**Files:**
- Create: `scripts/simulate/send_test_messages.py`
- Create: `scripts/simulate/fixtures/test_messages.json`

**Step 1: Create test message fixtures and simulation script**

**Step 2: Commit**

```bash
git add scripts/simulate/
git commit -m "feat: add synthetic test simulation script and fixtures"
```

---

## Execution Order Summary

| Task | Component | Depends On |
|------|-----------|------------|
| 1 | Project setup | — |
| 2 | Data models | 1 |
| 3 | Config loader | 2 |
| 4 | Twilio parser | 1 |
| 5 | Webhook Flask app | 4 |
| 6 | EXIF extraction | 1 |
| 7 | Image resizing | 1 |
| 8 | Dedup detection | 1 |
| 9 | Claude analysis | 1 |
| 10 | Curation logic | 1 |
| 11 | Manifest builder | 2, 10 |
| 12 | Frontend JS/CSS | 11 |
| 13 | GCS helpers | 1 |
| 14 | Firestore helpers | 2 |
| 15 | Wire webhook | 4, 5, 13, 14 |
| 16 | Batch orchestration | 6, 7, 8, 9, 10, 11, 13, 14 |
| 17 | Terraform base | — |
| 18 | Terraform resources | 17 |
| 19 | CLI scripts | 3, 14, 16 |
| 20 | Export tool | 11, 13 |
| 21 | CI | 1 |
| 22 | Test fixtures | 15, 16 |

**Parallelizable groups:**
- Tasks 2-4 can run in parallel after Task 1
- Tasks 6-10 can run in parallel after Task 1
- Tasks 13-14 can run in parallel after Task 2
- Tasks 17-18 can run at any time (independent of Python code)
