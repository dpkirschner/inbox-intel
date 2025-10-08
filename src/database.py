"""Database models and initialization for InboxIntel."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Message(Base):
    """Message model for storing guest messages from Guesty."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guesty_message_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reservation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    guest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_text: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    llm_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return (
            f"Message(id={self.id!r}, guesty_message_id={self.guesty_message_id!r}, "
            f"guest_name={self.guest_name!r}, is_processed={self.is_processed!r})"
        )


def init_database(database_url: str) -> None:
    """
    Initialize the database and create tables if they don't exist.

    Args:
        database_url: SQLAlchemy database URL (e.g., 'sqlite:///data/inbox_intel.db')
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)


def get_engine(database_url: str) -> Engine:
    """
    Create and return a database engine.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy Engine instance
    """
    return create_engine(database_url, echo=False)


def get_session(engine: Engine) -> Session:
    """
    Create and return a database session.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        SQLAlchemy Session instance
    """
    return Session(engine)
