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
