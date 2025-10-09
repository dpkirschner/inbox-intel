"""Tests for notification service functionality."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.notifications import (
    PushoverError,
    _send_slack_message,
    render_template,
    send_daily_summary,
    send_pushover_alert,
)


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


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_render_early_checkin_template(self):
        """Test rendering early check-in template."""
        result = render_template(
            "EARLY_CHECKIN",
            guest_name="John Doe",
            reservation_id="res_123",
            confidence="95%",
            summary="Guest wants to check in at 10am",
            message_text="Can we check in early at 10am?",
        )

        assert "John Doe" in result
        assert "res_123" in result
        assert "95%" in result
        assert "Guest wants to check in at 10am" in result
        assert "Can we check in early at 10am?" in result

    def test_render_maintenance_issue_template(self):
        """Test rendering maintenance issue template."""
        result = render_template(
            "MAINTENANCE_ISSUE",
            guest_name="Jane Smith",
            reservation_id="res_456",
            confidence="98%",
            summary="WiFi not working",
            message_text="The WiFi is down in our unit",
        )

        assert "Jane Smith" in result
        assert "res_456" in result
        assert "98%" in result
        assert "WiFi not working" in result
        assert "The WiFi is down in our unit" in result

    def test_render_template_with_defaults(self):
        """Test rendering template with default values."""
        result = render_template("EARLY_CHECKIN")

        assert "Unknown" in result
        assert "N/A" in result

    def test_render_template_partial_context(self):
        """Test rendering template with partial context."""
        result = render_template("SPECIAL_REQUEST", guest_name="Alice", summary="Extra towels")

        assert "Alice" in result
        assert "Extra towels" in result
        assert "N/A" in result

    def test_render_template_not_found(self):
        """Test rendering non-existent template raises error."""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            render_template("INVALID_CATEGORY")


class TestSendDailySummary:
    """Tests for send_daily_summary function."""

    @patch("src.notifications.send_pushover_alert")
    def test_send_daily_summary_via_pushover(self, mock_pushover):
        """Test sending daily summary via Pushover when configured."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = "test_token"
            mock_cfg.PUSHOVER_USER = "test_user"
            mock_cfg.SLACK_WEBHOOK_URL = ""
            mock_cfg.EMAIL_FROM = ""
            mock_cfg.EMAIL_TO = ""

            summary = "📅 **Daily Summary**\n- Test arrival"
            send_daily_summary(summary)

            mock_pushover.assert_called_once_with(
                "📅 Daily Arrival Summary",
                summary,
                priority=0,
            )

    @patch("src.notifications._send_slack_message")
    def test_send_daily_summary_via_slack(self, mock_slack):
        """Test sending daily summary via Slack when configured."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = ""
            mock_cfg.PUSHOVER_USER = ""
            mock_cfg.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
            mock_cfg.EMAIL_FROM = ""
            mock_cfg.EMAIL_TO = ""

            summary = "📅 **Daily Summary**\n- Test arrival"
            send_daily_summary(summary)

            mock_slack.assert_called_once_with(
                "📅 Daily Arrival Summary",
                summary,
            )

    @patch("src.notifications.send_pushover_alert")
    @patch("src.notifications._send_slack_message")
    def test_send_daily_summary_multiple_channels(self, mock_slack, mock_pushover):
        """Test sending daily summary via multiple channels."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = "test_token"
            mock_cfg.PUSHOVER_USER = "test_user"
            mock_cfg.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
            mock_cfg.EMAIL_FROM = ""
            mock_cfg.EMAIL_TO = ""

            summary = "📅 **Daily Summary**\n- Test arrival"
            send_daily_summary(summary)

            mock_pushover.assert_called_once()
            mock_slack.assert_called_once()

    @patch("src.notifications.send_pushover_alert")
    def test_send_daily_summary_pushover_error_raises(self, mock_pushover):
        """Test that Pushover errors are raised."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = "test_token"
            mock_cfg.PUSHOVER_USER = "test_user"
            mock_cfg.SLACK_WEBHOOK_URL = ""
            mock_cfg.EMAIL_FROM = ""
            mock_cfg.EMAIL_TO = ""

            mock_pushover.side_effect = PushoverError("API error")

            with pytest.raises(PushoverError):
                send_daily_summary("Test summary")

    @patch("src.notifications._send_slack_message")
    def test_send_daily_summary_slack_error_logged(self, mock_slack):
        """Test that Slack errors are logged but don't raise."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.PUSHOVER_TOKEN = ""
            mock_cfg.PUSHOVER_USER = ""
            mock_cfg.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
            mock_cfg.EMAIL_FROM = ""
            mock_cfg.EMAIL_TO = ""

            mock_slack.side_effect = Exception("Slack error")

            send_daily_summary("Test summary")


class TestSendSlackMessage:
    """Tests for _send_slack_message function."""

    def test_send_slack_message_success(self):
        """Test successful Slack message send."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"

            with patch("src.notifications.requests.post") as mock_post:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_post.return_value = mock_resp

                _send_slack_message("Test Title", "Test Message")

                mock_post.assert_called_once_with(
                    "https://hooks.slack.com/test",
                    json={
                        "text": "*Test Title*\n\nTest Message",
                        "mrkdwn": True,
                    },
                    timeout=10,
                )

    def test_send_slack_message_no_webhook_configured(self):
        """Test that error is raised when webhook not configured."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.SLACK_WEBHOOK_URL = ""

            with pytest.raises(ValueError, match="Slack webhook URL not configured"):
                _send_slack_message("Test", "Test")

    def test_send_slack_message_http_error(self):
        """Test handling of HTTP errors."""
        with patch("src.notifications.config") as mock_cfg:
            mock_cfg.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"

            with patch("src.notifications.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.HTTPError("HTTP error")

                with pytest.raises(requests.exceptions.HTTPError):
                    _send_slack_message("Test", "Test")
