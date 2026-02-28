import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
from batch.main import process_trip_batch
from shared.models import Message, TripConfig


@pytest.fixture
def mock_trip_config():
    return TripConfig.from_dict({
        "id": "uk-2026", "title": "England 2026", "destination": "London",
        "dates": {"start": "2026-05-21", "end": "2026-05-28"},
        "timezone": "Europe/London", "locations": [],
        "participants": [{"name": "Kevin", "phone": "+15551234567"}],
    })


class TestProcessTripBatch:
    @patch("batch.main.upload_blob")
    @patch("batch.main.mark_message_processed")
    @patch("batch.main.analyze_photo")
    @patch("batch.main.resize_image")
    @patch("batch.main.extract_exif")
    @patch("batch.main.download_blob")
    @patch("batch.main.get_unprocessed_messages")
    @patch("batch.main.load_trip_config")
    def test_processes_photo_message(
        self, mock_load_config, mock_get_msgs, mock_download, mock_exif,
        mock_resize, mock_analyze, mock_mark, mock_upload, mock_trip_config,
    ):
        mock_load_config.return_value = mock_trip_config

        mock_get_msgs.return_value = [
            Message(
                id="msg-1", trip_id="uk-2026", sender_phone="+15551234567",
                sender_name="Kevin", timestamp=datetime(2026, 5, 22, 14, 30),
                text="Cool view!", media_urls=["uk-2026/raw/photo.jpg"],
                processed=False,
            )
        ]
        mock_download.return_value = b"fake-image"
        mock_exif.return_value = {"timestamp": datetime(2026, 5, 22, 14, 30)}
        mock_resize.return_value = b"resized-image"
        mock_analyze.return_value = {
            "caption": "A view", "category": "sightseeing",
            "quality": 7, "alt": "A nice view",
        }

        process_trip_batch("uk-2026", config_path="/fake/trip.yaml", dry_run=True)

        mock_get_msgs.assert_called_once_with("uk-2026")
        assert mock_download.called
        assert mock_resize.called
        assert mock_analyze.called

    @patch("batch.main.upload_blob")
    @patch("batch.main.mark_message_processed")
    @patch("batch.main.get_unprocessed_messages")
    @patch("batch.main.load_trip_config")
    def test_no_messages_is_noop(
        self, mock_load_config, mock_get_msgs, mock_mark, mock_upload, mock_trip_config,
    ):
        mock_load_config.return_value = mock_trip_config
        mock_get_msgs.return_value = []

        process_trip_batch("uk-2026", config_path="/fake/trip.yaml", dry_run=True)

        mock_get_msgs.assert_called_once()
        mock_mark.assert_not_called()
        mock_upload.assert_not_called()
