"""Main application module with FastAPI webhook server."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .config import config
from .database import get_engine, get_session, init_database, save_message_from_webhook
from .logger import logger
from .polling import fetch_and_save_messages
from .worker import process_unclassified_messages

# Global engine instance
_engine = None
_scheduler = None


class WebhookMessage(BaseModel):
    """Model for Guesty webhook message payload."""

    model_config = {"populate_by_name": True}

    event: str
    reservation_id: str | None = Field(None, alias="reservationId")
    conversation: dict[str, Any] | None = None
    message: dict[str, Any]


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    success: bool
    message_id: str | None = None
    is_duplicate: bool = False


def get_db() -> Iterator[Session]:
    """Database session dependency."""
    global _engine
    if _engine is None:
        _engine = get_engine(config.DATABASE_URL)
    session = get_session(_engine)
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    global _engine, _scheduler
    logger.info("Starting InboxIntel application")
    if _engine is None:
        _engine = get_engine(config.DATABASE_URL)
        init_database(config.DATABASE_URL)
        logger.info(f"Database initialized at {config.DATABASE_URL}")
    else:
        logger.info("Using existing engine (test mode)")

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        fetch_and_save_messages,
        trigger="interval",
        minutes=config.POLLING_INTERVAL_MINUTES,
        kwargs={"minutes_lookback": config.POLLING_INTERVAL_MINUTES},
        id="message_polling",
        name="Poll Guesty API for new messages",
        replace_existing=True,
    )
    _scheduler.add_job(
        process_unclassified_messages,
        trigger="interval",
        seconds=config.PROCESSING_INTERVAL_SECONDS,
        id="message_processing",
        name="Process unclassified messages",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Scheduler started: polling every {config.POLLING_INTERVAL_MINUTES} minutes")
    logger.info(
        f"Scheduler started: processing every {config.PROCESSING_INTERVAL_SECONDS} seconds"
    )

    yield

    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
    logger.info("Shutting down InboxIntel application")


app = FastAPI(
    title="InboxIntel",
    description="Self-hosted service for monitoring Guesty guest messages",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for health check."""
    return {"status": "ok", "service": "InboxIntel"}


@app.post("/webhooks/guesty/messages", response_model=WebhookResponse)
async def receive_guesty_webhook(
    payload: WebhookMessage, db: Session = Depends(get_db)
) -> WebhookResponse:
    """
    Receive and process Guesty message webhooks.

    Expected events:
    - reservation.messageReceived
    - reservation.messageSent
    """
    logger.info(f"Received webhook: {payload.event}")

    if payload.event not in ["reservation.messageReceived", "reservation.messageSent"]:
        logger.warning(f"Unsupported event type: {payload.event}")
        raise HTTPException(status_code=400, detail=f"Unsupported event: {payload.event}")

    if not payload.message:
        logger.error("Webhook payload missing 'message' field")
        raise HTTPException(status_code=400, detail="Missing 'message' field in payload")

    message_data = payload.message
    message_id = message_data.get("_id")
    message_text = message_data.get("body", "")
    created_at_str = message_data.get("createdAt")

    if not message_id:
        logger.error("Message missing '_id' field")
        raise HTTPException(status_code=400, detail="Message missing '_id' field")

    if not message_text:
        logger.warning(f"Message {message_id} has empty body")

    try:
        if created_at_str:
            timestamp = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.utcnow()
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse timestamp: {e}")
        timestamp = datetime.utcnow()

    conversation_id = None
    if payload.conversation:
        conversation_id = payload.conversation.get("_id")

    guest_name = message_data.get("from")

    try:
        saved_message = save_message_from_webhook(
            session=db,
            message_id=message_id,
            message_text=message_text,
            timestamp=timestamp,
            conversation_id=conversation_id,
            reservation_id=payload.reservation_id,
            guest_name=guest_name,
        )

        if saved_message:
            logger.info(f"Saved new message: {message_id}")
            return WebhookResponse(success=True, message_id=message_id, is_duplicate=False)
        else:
            logger.info(f"Duplicate message skipped: {message_id}")
            return WebhookResponse(success=True, message_id=message_id, is_duplicate=True)

    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        raise HTTPException(status_code=500, detail="Failed to save message") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=config.WEBHOOK_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )
