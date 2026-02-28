import pytest
from webhook.twilio_handler import parse_twilio_request, TwilioMessage


class TestParseTwilioRequest:
    def test_parse_text_only_message(self):
        form_data = {
            "From": "+15551234567",
            "Body": "Just landed!",
            "NumMedia": "0",
            "MessageSid": "SM1234567890",
        }
        msg = parse_twilio_request(form_data)
        assert msg.sender == "+15551234567"
        assert msg.body == "Just landed!"
        assert msg.media_urls == []
        assert msg.message_sid == "SM1234567890"

    def test_parse_message_with_one_photo(self):
        form_data = {
            "From": "+15551234567",
            "Body": "Check this out!",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/123.jpg",
            "MediaContentType0": "image/jpeg",
            "MessageSid": "SM9876543210",
        }
        msg = parse_twilio_request(form_data)
        assert len(msg.media_urls) == 1
        assert msg.media_urls[0] == "https://api.twilio.com/media/123.jpg"
        assert msg.media_content_types[0] == "image/jpeg"

    def test_parse_message_with_multiple_photos(self):
        form_data = {
            "From": "+15559876543",
            "Body": "",
            "NumMedia": "2",
            "MediaUrl0": "https://api.twilio.com/media/a.jpg",
            "MediaContentType0": "image/jpeg",
            "MediaUrl1": "https://api.twilio.com/media/b.png",
            "MediaContentType1": "image/png",
            "MessageSid": "SM1111111111",
        }
        msg = parse_twilio_request(form_data)
        assert len(msg.media_urls) == 2
        assert msg.body == ""

    def test_parse_empty_body_and_no_media(self):
        form_data = {
            "From": "+15551234567",
            "Body": "",
            "NumMedia": "0",
            "MessageSid": "SM0000000000",
        }
        msg = parse_twilio_request(form_data)
        assert msg.body == ""
        assert msg.media_urls == []
