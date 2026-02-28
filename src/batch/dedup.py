from __future__ import annotations
import io
from PIL import Image


def compute_hash(image_data: bytes, hash_size: int = 8) -> int:
    """Compute a difference hash (dHash) for near-duplicate detection.

    dHash compares adjacent pixels to detect gradients, making it more robust
    than average hash for solid-color or low-contrast images.
    """
    img = Image.open(io.BytesIO(image_data)).convert("L")
    # Resize to (hash_size + 1) x hash_size so we can compare adjacent columns
    img = img.resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = list(img.tobytes())
    width = hash_size + 1
    result = 0
    bit = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * width + col]
            right = pixels[row * width + col + 1]
            if left > right:
                result |= 1 << bit
            bit += 1
    return result


def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")


def find_duplicates(items: list[dict], threshold: int = 5) -> set[str]:
    hashes = []
    for item in items:
        h = compute_hash(item["image_data"])
        hashes.append((item["id"], h, item.get("quality", 0)))
    to_remove = set()
    for i in range(len(hashes)):
        if hashes[i][0] in to_remove:
            continue
        for j in range(i + 1, len(hashes)):
            if hashes[j][0] in to_remove:
                continue
            dist = hamming_distance(hashes[i][1], hashes[j][1])
            if dist <= threshold:
                if hashes[i][2] >= hashes[j][2]:
                    to_remove.add(hashes[j][0])
                else:
                    to_remove.add(hashes[i][0])
    return to_remove
