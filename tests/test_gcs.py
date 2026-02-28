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
