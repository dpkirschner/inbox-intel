"""Tests for LLM classifier module."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.llm_classifier import (
    CLASSIFICATION_PROMPT,
    ClassificationResult,
    classify_message,
)


class TestClassificationResult:
    def test_to_dict(self):
        result = ClassificationResult(
            category="EARLY_CHECKIN", confidence=0.95, summary="Guest wants early check-in at 10am"
        )
        expected = {
            "category": "EARLY_CHECKIN",
            "confidence": 0.95,
            "summary": "Guest wants early check-in at 10am",
        }
        assert result.to_dict() == expected


class TestClassifyMessage:
    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_with_openai_early_checkin(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "category": "EARLY_CHECKIN",
                            "confidence": 0.95,
                            "summary": "Guest requests early check-in at 10am",
                        }
                    )
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = classify_message("Hi! Our flight lands at 10am, can we check in early?")

        assert result.category == "EARLY_CHECKIN"
        assert result.confidence == 0.95
        assert "10am" in result.summary

        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4-turbo"
        assert call_args.kwargs["temperature"] == 0.2

    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_with_openai_late_checkout(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "category": "LATE_CHECKOUT",
                            "confidence": 0.92,
                            "summary": "Guest needs to check out at 2pm instead of 11am",
                        }
                    )
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = classify_message("Can we check out at 2pm? Our flight is at 5pm.")

        assert result.category == "LATE_CHECKOUT"
        assert result.confidence == 0.92
        assert "2pm" in result.summary

    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_with_openai_maintenance_issue(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "category": "MAINTENANCE_ISSUE",
                            "confidence": 0.98,
                            "summary": "WiFi not working in the unit",
                        }
                    )
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = classify_message("The WiFi isn't working. Can you help?")

        assert result.category == "MAINTENANCE_ISSUE"
        assert result.confidence == 0.98

    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_with_openai_special_request(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "category": "SPECIAL_REQUEST",
                            "confidence": 0.90,
                            "summary": "Guest needs extra towels and a crib",
                        }
                    )
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = classify_message("Could we get some extra towels and a crib for the baby?")

        assert result.category == "SPECIAL_REQUEST"
        assert result.confidence == 0.90

    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_with_openai_general_question(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "category": "GENERAL_QUESTION",
                            "confidence": 0.85,
                            "summary": "Guest asking about parking options",
                        }
                    )
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = classify_message("Where should we park?")

        assert result.category == "GENERAL_QUESTION"
        assert result.confidence == 0.85

    @patch("src.llm_classifier.config")
    def test_classify_with_ollama(self, mock_config):
        mock_config.LLM_PROVIDER = "ollama:llama3"

        with patch("requests.post") as mock_requests_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "response": json.dumps(
                    {
                        "category": "EARLY_CHECKIN",
                        "confidence": 0.93,
                        "summary": "Guest wants to check in early",
                    }
                )
            }
            mock_requests_post.return_value = mock_response

            result = classify_message("Can we arrive at noon?")

            assert result.category == "EARLY_CHECKIN"
            assert result.confidence == 0.93

            mock_requests_post.assert_called_once()
            call_args = mock_requests_post.call_args
            assert "http://localhost:11434/api/generate" in call_args[0][0]
            assert call_args.kwargs["json"]["model"] == "llama3"
            assert call_args.kwargs["json"]["format"] == "json"

    @patch("src.llm_classifier.OpenAI")
    @patch("src.llm_classifier.config")
    def test_classify_handles_empty_response(self, mock_config, mock_openai_class):
        mock_config.LLM_PROVIDER = "openai:gpt-4-turbo"
        mock_config.OPENAI_API_KEY = "test-key"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=None))]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with pytest.raises(ValueError, match="Empty response from OpenAI"):
            classify_message("test message")

    @patch("src.llm_classifier.config")
    def test_classify_unsupported_provider(self, mock_config):
        mock_config.LLM_PROVIDER = "unsupported:model"

        with pytest.raises(ValueError, match="Unsupported LLM provider: unsupported"):
            classify_message("test message")

    def test_classification_prompt_format(self):
        prompt = CLASSIFICATION_PROMPT.format(message_text="test message")
        assert "test message" in prompt
        assert "EARLY_CHECKIN" in prompt
        assert "LATE_CHECKOUT" in prompt
        assert "SPECIAL_REQUEST" in prompt
        assert "MAINTENANCE_ISSUE" in prompt
        assert "GENERAL_QUESTION" in prompt
