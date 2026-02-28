# tests/test_analyze.py
import pytest
import json
from unittest.mock import patch, MagicMock
from batch.analyze import analyze_photo, analyze_text_message, build_photo_prompt


class TestBuildPhotoPrompt:
    def test_includes_trip_context(self):
        prompt = build_photo_prompt(
            day_number=2,
            destination="London & Cornwall",
            planned_locations=["Borough Market", "Shakespeare's Globe"],
            time="14:30",
            location="South Bank",
            sender_name="Kevin",
        )
        assert "Day 2" in prompt
        assert "London & Cornwall" in prompt
        assert "Borough Market" in prompt
        assert "Kevin" in prompt
        assert "14:30" in prompt


class TestAnalyzePhoto:
    @patch("batch.analyze.get_anthropic_client")
    def test_returns_expected_fields(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "caption": "A beautiful view from the Globe Theatre.",
                    "category": "sightseeing",
                    "quality": 8,
                    "alt": "View from the Globe Theatre over the Thames",
                })
            )
        ]
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyze_photo(
            image_data=b"fake-image-data",
            day_number=2,
            destination="London",
            planned_locations=["Globe Theatre"],
            time="14:30",
            location="South Bank",
            sender_name="Kevin",
        )
        assert result["caption"] == "A beautiful view from the Globe Theatre."
        assert result["category"] == "sightseeing"
        assert result["quality"] == 8
        assert "alt" in result


class TestAnalyzeTextMessage:
    @patch("batch.analyze.get_anthropic_client")
    def test_classifies_text_message(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"type": "quote"}))
        ]
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyze_text_message("This cream tea is incredible")
        assert result["type"] == "quote"
