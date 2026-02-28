import pytest
import io
from PIL import Image
from PIL.ExifTags import Base as ExifBase


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
    """JPEG with EXIF GPS data."""
    img = Image.new("RGB", (100, 100), "green")
    exif = img.getexif()

    # GPS IFD
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
