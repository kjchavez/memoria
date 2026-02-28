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
