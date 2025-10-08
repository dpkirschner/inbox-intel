"""Background worker for processing unclassified messages."""

from sqlalchemy import select

from src.config import config
from src.database import Message, get_engine, get_session
from src.llm_classifier import ClassificationResult, classify_message
from src.logger import get_logger
from src.notifications import PushoverError, render_template, send_pushover_alert

logger = get_logger(__name__)


def process_unclassified_messages() -> int:
    engine = get_engine(config.DATABASE_URL)
    session = get_session(engine)

    try:
        stmt = select(Message).where(~Message.is_processed)
        unprocessed_messages = session.execute(stmt).scalars().all()

        if not unprocessed_messages:
            logger.debug("No unprocessed messages found")
            return 0

        logger.info(f"Processing {len(unprocessed_messages)} unclassified messages")

        processed_count = 0
        for message in unprocessed_messages:
            try:
                result = classify_message(message.message_text)

                message.llm_category = result.category
                message.llm_summary = result.summary
                message.llm_confidence = result.confidence
                message.is_processed = True

                session.commit()
                processed_count += 1

                logger.info(
                    f"Classified message {message.guesty_message_id}: "
                    f"{result.category} (confidence: {result.confidence:.2f})"
                )

                if _should_send_alert(result.category, result.confidence):
                    _send_classification_alert(message, result)

            except Exception as e:
                logger.error(
                    f"Failed to classify message {message.guesty_message_id}: {e}"
                )
                session.rollback()
                continue

        logger.info(f"Successfully processed {processed_count} messages")
        return processed_count

    except Exception as e:
        logger.error(f"Error in process_unclassified_messages: {e}")
        session.rollback()
        raise

    finally:
        session.close()


def _should_send_alert(category: str, confidence: float) -> bool:
    return (
        category in config.ALERT_CATEGORIES
        and confidence >= config.MIN_CONFIDENCE_THRESHOLD
    )


def _send_classification_alert(message: Message, result: ClassificationResult) -> None:
    try:
        title = f"🔔 {result.category.replace('_', ' ').title()}"

        alert_message = render_template(
            result.category,
            guest_name=message.guest_name or "Unknown",
            reservation_id=message.reservation_id or "N/A",
            confidence=f"{result.confidence:.0%}",
            summary=result.summary,
            message_text=message.message_text[:200],
        )

        send_pushover_alert(title, alert_message, priority=0)
        logger.info(f"Alert sent for message {message.guesty_message_id}")

    except (PushoverError, FileNotFoundError) as e:
        logger.warning(f"Failed to send alert for {message.guesty_message_id}: {e}")
