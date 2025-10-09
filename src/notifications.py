"""Notification service for sending alerts via Pushover and other channels."""

import logging
from pathlib import Path

import requests

from src.config import config

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class PushoverError(Exception):
    """Exception raised when Pushover API call fails."""

    pass


def send_pushover_alert(title: str, message: str, priority: int = 0) -> None:
    """
    Send a push notification via Pushover.

    Args:
        title: Notification title
        message: Notification message body
        priority: Priority level (-2 to 2, default 0)

    Raises:
        PushoverError: If the API call fails or credentials are missing
    """
    if not config.PUSHOVER_TOKEN or not config.PUSHOVER_USER:
        raise PushoverError("Pushover credentials not configured")

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": config.PUSHOVER_TOKEN,
        "user": config.PUSHOVER_USER,
        "title": title,
        "message": message,
        "priority": priority,
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if result.get("status") != 1:
            errors = result.get("errors", ["Unknown error"])
            raise PushoverError(f"Pushover API error: {errors}")

        logger.info(f"Pushover notification sent: {title}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Pushover notification: {e}")
        raise PushoverError(f"Failed to send notification: {e}") from e


def send_daily_summary(summary: str) -> None:
    """
    Send daily summary report via configured notification channels.

    Args:
        summary: Markdown-formatted daily summary report

    Raises:
        PushoverError: If Pushover notification fails
    """
    title = "📅 Daily Arrival Summary"

    if config.PUSHOVER_TOKEN and config.PUSHOVER_USER:
        try:
            send_pushover_alert(title, summary, priority=0)
            logger.info("Daily summary sent via Pushover")
        except PushoverError as e:
            logger.error(f"Failed to send daily summary via Pushover: {e}")
            raise

    if config.SLACK_WEBHOOK_URL:
        try:
            _send_slack_message(title, summary)
            logger.info("Daily summary sent via Slack")
        except Exception as e:
            logger.error(f"Failed to send daily summary via Slack: {e}")

    if config.EMAIL_FROM and config.EMAIL_TO:
        logger.warning("Email delivery not yet implemented for daily summaries")


def _send_slack_message(title: str, message: str) -> None:
    """
    Send a message to Slack via webhook.

    Args:
        title: Message title
        message: Message body (markdown supported)

    Raises:
        requests.exceptions.RequestException: If the webhook call fails
    """
    if not config.SLACK_WEBHOOK_URL:
        raise ValueError("Slack webhook URL not configured")

    payload = {
        "text": f"*{title}*\n\n{message}",
        "mrkdwn": True,
    }

    try:
        response = requests.post(
            config.SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"Slack message sent: {title}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Slack message: {e}")
        raise


def render_template(category: str, **context: str) -> str:
    """
    Render a notification template with the provided context.

    Args:
        category: Message category (e.g., EARLY_CHECKIN, MAINTENANCE_ISSUE)
        **context: Template variables (guest_name, reservation_id, etc.)

    Returns:
        Rendered template string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_name = f"{category.lower()}_alert.md"
    template_path = TEMPLATES_DIR / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template_content = template_path.read_text()

    context_defaults = {
        "guest_name": "Unknown",
        "reservation_id": "N/A",
        "confidence": "N/A",
        "summary": "N/A",
        "message_text": "N/A",
    }
    context_defaults.update(context)

    return template_content.format(**context_defaults)
