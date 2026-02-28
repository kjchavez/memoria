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
    db = get_db()
    collection = db.collection("trips").document(msg.trip_id).collection("messages")
    _, doc_ref = collection.add(msg.to_dict())
    return doc_ref.id


def get_unprocessed_messages(trip_id: str) -> list[Message]:
    db = get_db()
    collection = db.collection("trips").document(trip_id).collection("messages")
    query = collection.where("processed", "==", False)
    messages = []
    for doc in query.stream():
        messages.append(Message.from_dict(doc.id, doc.to_dict()))
    return messages


def mark_message_processed(trip_id: str, message_id: str) -> None:
    db = get_db()
    doc_ref = (
        db.collection("trips")
        .document(trip_id)
        .collection("messages")
        .document(message_id)
    )
    doc_ref.update({"processed": True})


def get_trip_config_doc(trip_id: str) -> dict | None:
    db = get_db()
    doc = db.collection("trips").document(trip_id).get()
    if doc.exists:
        return doc.to_dict()
    return None
