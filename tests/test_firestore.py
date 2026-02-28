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
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "generated-id"
        mock_collection.add.return_value = (None, mock_doc_ref)

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


class TestGetTripConfigDoc:
    @patch("shared.firestore.get_db")
    def test_returns_dict_when_exists(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"id": "uk-2026", "title": "UK Trip"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = get_trip_config_doc("uk-2026")
        assert result == {"id": "uk-2026", "title": "UK Trip"}

    @patch("shared.firestore.get_db")
    def test_returns_none_when_missing(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = get_trip_config_doc("nonexistent")
        assert result is None
