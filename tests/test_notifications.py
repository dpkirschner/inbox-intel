"""Tests for notification service functionality."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.notifications import PushoverError, send_pushover_alert


@pytest.fixture
def mock_config():
    """Mock configuration values."""
    with patch("src.notifications.config") as mock_cfg:
        mock_cfg.PUSHOVER_TOKEN = "test_token"
        mock_cfg.PUSHOVER_USER = "test_user"
        yield mock_cfg


@pytest.fixture
def mock_success_response():
    """Mock successful Pushover API response."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": 1, "request": "test_request_id"}
    return mock_resp


class TestSendPushoverAlert:
    """Tests for send_pushover_alert function."""

    def test_send_alert_success(self, mock_config, mock_success_response):
        """Test successful notification send."""
        with patch("src.notifications.requests.post") as mock_post:
            mock_post.return_value = mock_success_response

            send_pushover_alert("Test Title", "Test Message")

            mock_post.assert_called_once_with(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": "test_token",
                    "user": "test_user",
                    "title": "Test Title",
                    "message": "Test Message",
                    "priority": 0,
                },
                timeout=10,
            )

    def test_send_alert_with_priority(self, mock_config, mock_success_response):
        """Test notification with custom priority."""
        with patch("src.notifications.requests.post") as mock_post:
            mock_post.return_value = mock_success_response

            send_pushover_alert("Urgent", "Critical issue", priority=1)

            call_args = mock_post.call_args
            assert call_args[1]["data"]["priority"] == 1

    def test_missing_token_raises_error(self):
        """Test that missing token raises PushoverError."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = ""
            mock_cfg.PUSHOVER_USER = "test_user"

            with pytest.raises(PushoverError, match="credentials not configured"):
                send_pushover_alert("Title", "Message")

    def test_missing_user_raises_error(self):
        """Test that missing user raises PushoverError."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = "test_token"
            mock_cfg.PUSHOVER_USER = ""

            with pytest.raises(PushoverError, match="credentials not configured"):
                send_pushover_alert("Title", "Message")

    def test_api_error_response(self, mock_config):
        """Test handling of API error response."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": 0,
            "errors": ["invalid token"],
        }

        with patch("src.notifications.requests.post") as mock_post:
            mock_post.return_value = mock_resp

            with pytest.raises(PushoverError, match="Pushover API error"):
                send_pushover_alert("Title", "Message")

    def test_http_error(self, mock_config):
        """Test handling of HTTP errors."""
        with patch("src.notifications.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.HTTPError("400 Bad Request")

            with pytest.raises(PushoverError, match="Failed to send notification"):
                send_pushover_alert("Title", "Message")

    def test_network_timeout(self, mock_config):
        """Test handling of network timeout."""
        with patch("src.notifications.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

            with pytest.raises(PushoverError, match="Failed to send notification"):
                send_pushover_alert("Title", "Message")

    def test_connection_error(self, mock_config):
        """Test handling of connection errors."""
        with patch("src.notifications.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("No network")

            with pytest.raises(PushoverError, match="Failed to send notification"):
                send_pushover_alert("Title", "Message")
