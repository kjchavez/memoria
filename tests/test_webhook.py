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


import json
from unittest.mock import patch, MagicMock
from webhook.main import create_app


@pytest.fixture
def app():
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestWebhookEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"

    @patch("webhook.main.process_incoming_message")
    def test_incoming_sms_from_known_participant(self, mock_process, client):
        mock_process.return_value = None
        resp = client.post(
            "/webhook/sms",
            data={
                "From": "+15551234567",
                "Body": "Just landed!",
                "NumMedia": "0",
                "MessageSid": "SM123",
            },
        )
        assert resp.status_code == 200
        assert "twiml" in resp.content_type.lower() or resp.status_code == 200
        mock_process.assert_called_once()

    @patch("webhook.main.process_incoming_message")
    def test_incoming_mms_with_photo(self, mock_process, client):
        mock_process.return_value = None
        resp = client.post(
            "/webhook/sms",
            data={
                "From": "+15551234567",
                "Body": "Look!",
                "NumMedia": "1",
                "MediaUrl0": "https://api.twilio.com/media/123.jpg",
                "MediaContentType0": "image/jpeg",
                "MessageSid": "SM456",
            },
        )
        assert resp.status_code == 200
        mock_process.assert_called_once()
