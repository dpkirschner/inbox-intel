"""Background worker for processing unclassified messages."""

from sqlalchemy import select

from src.config import config
from src.database import Message, get_engine, get_session
from src.llm_classifier import classify_message
from src.logger import get_logger

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
