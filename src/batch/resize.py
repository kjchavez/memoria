from __future__ import annotations
import io
from PIL import Image


def resize_image(image_data: bytes, max_dimension: int = 1600) -> bytes:
    """Resize so longest side is at most max_dimension. No upscale. Returns JPEG bytes."""
    img = Image.open(io.BytesIO(image_data))
    if max(img.size) <= max_dimension:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    ratio = max_dimension / max(img.size)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
