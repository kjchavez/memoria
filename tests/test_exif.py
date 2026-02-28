import pytest
from datetime import datetime
from batch.exif import extract_exif
from PIL import Image
import io


class TestExtractExif:
    def test_extract_from_jpeg_with_exif(self, sample_photo_with_exif):
        result = extract_exif(sample_photo_with_exif)
        assert result is not None

    def test_extract_from_bytes_without_exif(self):
        img = Image.new("RGB", (100, 100), "red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = extract_exif(buf.getvalue())
        assert result == {}

    def test_extract_returns_timestamp_when_present(self, jpeg_with_timestamp):
        result = extract_exif(jpeg_with_timestamp)
        assert "timestamp" in result
        assert isinstance(result["timestamp"], datetime)
        assert result["timestamp"] == datetime(2026, 5, 22, 14, 30, 0)

    def test_extract_returns_gps_when_present(self, jpeg_with_gps):
        result = extract_exif(jpeg_with_gps)
        assert "gps" in result
        assert "lat" in result["gps"]
        assert "lng" in result["gps"]
