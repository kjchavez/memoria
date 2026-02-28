from __future__ import annotations

import io
from datetime import datetime

from PIL import Image
from PIL.ExifTags import Base as ExifBase, GPS, IFD


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

    # GPS — Pillow stores GPS as a sub-IFD, access via get_ifd()
    gps_info = exif.get_ifd(IFD.GPSInfo)
    if gps_info:
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
    if dms is None or ref is None:
        return None
    degrees, minutes, seconds = dms
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal
