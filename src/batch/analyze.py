from __future__ import annotations

import base64
import json
import logging

import anthropic

logger = logging.getLogger(__name__)

_client = None


def get_anthropic_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def build_photo_prompt(
    day_number: int,
    destination: str,
    planned_locations: list[str],
    time: str,
    location: str,
    sender_name: str,
) -> str:
    locations_str = ", ".join(planned_locations) if planned_locations else "various locations"
    return f"""This is a photo from Day {day_number} of a trip to {destination}.
Today's planned locations: {locations_str}.
The photo was taken at {time} near {location}.
It was sent by {sender_name}.

Please provide a JSON object with exactly these fields:
1. "caption": A natural, warm caption (1-2 sentences)
2. "category": One of: sightseeing, food, sports, nature, group, transport, nightlife
3. "quality": Score 1-10 (composition, sharpness, visual interest)
4. "alt": Brief description for accessibility (alt text)

Respond with ONLY the JSON object, no other text."""


def analyze_photo(
    image_data: bytes,
    day_number: int,
    destination: str,
    planned_locations: list[str],
    time: str,
    location: str,
    sender_name: str,
) -> dict:
    client = get_anthropic_client()
    prompt = build_photo_prompt(
        day_number=day_number,
        destination=destination,
        planned_locations=planned_locations,
        time=time,
        location=location,
        sender_name=sender_name,
    )
    b64_image = base64.b64encode(image_data).decode("utf-8")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return json.loads(response.content[0].text)


def analyze_text_message(text: str) -> dict:
    client = get_anthropic_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": (
                    "Classify this text message from a trip participant into one category.\n\n"
                    f'Message: "{text}"\n\n'
                    'Respond with ONLY a JSON object: {"type": "quote"|"reaction"|"story"}'
                ),
            }
        ],
    )
    return json.loads(response.content[0].text)
