"""Message polling module for periodic Guesty API checks."""

from datetime import UTC, datetime, timedelta

from .config import config
from .database import get_engine, get_session, save_message_from_webhook
from .guesty_client import GuestyClient
from .logger import logger


def fetch_and_save_messages(minutes_lookback: int = 5) -> int:
    """
    Fetch messages from Guesty API created in the last X minutes and save to database.

    Args:
        minutes_lookback: Number of minutes to look back for messages (default: 5)

    Returns:
        Number of new messages saved
    """
    client = GuestyClient()
    engine = get_engine(config.DATABASE_URL)
    session = get_session(engine)

    try:
        cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes_lookback)
        logger.info(f"Polling Guesty API for messages since {cutoff_time.isoformat()}")

        params = {
            "createdFrom": cutoff_time.isoformat(),
            "limit": 100,
            "sort": "createdAt",
        }

        response = client._make_request(
            "GET", "communication/conversations/messages", params=params
        )

        messages_data = response.get("results", [])
        logger.info(f"Found {len(messages_data)} messages from API")

        new_messages_count = 0

        for msg in messages_data:
            message_id = msg.get("_id")
            message_text = msg.get("body", "")
            created_at_str = msg.get("createdAt")

            if not message_id:
                logger.warning("Message missing '_id', skipping")
                continue

            try:
                if created_at_str:
                    timestamp = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(UTC)
            except (ValueError, AttributeError) as e:
                logger.error(f"Failed to parse timestamp for message {message_id}: {e}")
                timestamp = datetime.now(UTC)

            conversation_id = msg.get("conversationId")
            reservation_id = msg.get("reservationId")
            guest_name = msg.get("from")

            saved = save_message_from_webhook(
                session=session,
                message_id=message_id,
                message_text=message_text,
                timestamp=timestamp,
                conversation_id=conversation_id,
                reservation_id=reservation_id,
                guest_name=guest_name,
            )

            if saved:
                new_messages_count += 1
                logger.info(f"Saved new message from polling: {message_id}")

        logger.info(f"Polling complete: {new_messages_count} new messages saved")
        return new_messages_count

    except Exception as e:
        logger.error(f"Error during message polling: {e}")
        raise
    finally:
        session.close()
