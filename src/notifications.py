"""Notification service for sending alerts via Pushover and other channels."""

import logging

import requests

from src.config import config

logger = logging.getLogger(__name__)


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
