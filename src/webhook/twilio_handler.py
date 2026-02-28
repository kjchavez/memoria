from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TwilioMessage:
    sender: str
    body: str
    media_urls: list[str]
    media_content_types: list[str]
    message_sid: str


def parse_twilio_request(form_data: dict) -> TwilioMessage:
    """Parse a Twilio webhook POST form into a TwilioMessage."""
    num_media = int(form_data.get("NumMedia", "0"))
    media_urls = []
    media_content_types = []
    for i in range(num_media):
        url = form_data.get(f"MediaUrl{i}")
        content_type = form_data.get(f"MediaContentType{i}", "")
        if url:
            media_urls.append(url)
            media_content_types.append(content_type)

    return TwilioMessage(
        sender=form_data.get("From", ""),
        body=form_data.get("Body", ""),
        media_urls=media_urls,
        media_content_types=media_content_types,
        message_sid=form_data.get("MessageSid", ""),
    )
