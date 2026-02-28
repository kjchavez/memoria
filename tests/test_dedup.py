import io
import pytest
from PIL import Image, ImageDraw
from batch.dedup import compute_hash, find_duplicates


def _make_patterned_image(seed: int, size: tuple[int, int] = (100, 100)) -> Image.Image:
    """Create an image with a unique pattern based on seed for reliable hashing."""
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    # Draw distinct geometric patterns based on seed
    colors = ["red", "blue", "green", "yellow", "purple", "orange"]
    c = colors[seed % len(colors)]
    draw.rectangle([seed * 5, seed * 5, 50 + seed * 10, 50 + seed * 10], fill=c)
    draw.ellipse([10 + seed * 3, 10 + seed * 3, 80 - seed * 2, 80 - seed * 2], fill=c)
    return img


class TestComputeHash:
    def _make_image_bytes(self, seed: int, size=(100, 100)) -> bytes:
        img = _make_patterned_image(seed, size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_same_image_same_hash(self):
        data = self._make_image_bytes(1)
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        assert h1 == h2

    def test_different_images_different_hash(self):
        h1 = compute_hash(self._make_image_bytes(1))
        h2 = compute_hash(self._make_image_bytes(2))
        assert h1 != h2

    def test_slightly_resized_images_similar_hash(self):
        img = _make_patterned_image(1, (200, 200))
        buf1 = io.BytesIO()
        img.save(buf1, format="JPEG", quality=95)
        buf2 = io.BytesIO()
        img.save(buf2, format="JPEG", quality=50)
        h1 = compute_hash(buf1.getvalue())
        h2 = compute_hash(buf2.getvalue())
        assert h1 == h2


class TestFindDuplicates:
    def _make_image_bytes(self, seed: int) -> bytes:
        img = _make_patterned_image(seed)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_no_duplicates(self):
        items = [
            {"id": "a", "image_data": self._make_image_bytes(1)},
            {"id": "b", "image_data": self._make_image_bytes(2)},
            {"id": "c", "image_data": self._make_image_bytes(3)},
        ]
        dupes = find_duplicates(items)
        assert dupes == set()

    def test_finds_exact_duplicates(self):
        same_image = self._make_image_bytes(1)
        items = [
            {"id": "a", "image_data": same_image, "quality": 8},
            {"id": "b", "image_data": same_image, "quality": 5},
            {"id": "c", "image_data": self._make_image_bytes(2), "quality": 7},
        ]
        dupes = find_duplicates(items)
        assert "b" in dupes
        assert "a" not in dupes
