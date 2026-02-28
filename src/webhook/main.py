from __future__ import annotations

import logging

from flask import Flask, request, Response

from webhook.twilio_handler import parse_twilio_request

logger = logging.getLogger(__name__)


def process_incoming_message(twilio_msg, form_data):
    """Process an incoming message. Stubbed — will be wired to GCS/Firestore later."""
    logger.info(
        "Received message from %s: %s (media: %d)",
        twilio_msg.sender,
        twilio_msg.body[:50] if twilio_msg.body else "(no text)",
        len(twilio_msg.media_urls),
    )


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/webhook/sms")
    def incoming_sms():
        twilio_msg = parse_twilio_request(request.form)
        process_incoming_message(twilio_msg, request.form)

        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Got it!</Message></Response>'
        return Response(twiml, content_type="application/xml")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
