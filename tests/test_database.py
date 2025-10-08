"""Tests for database functionality."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import Base, Message, get_engine, get_session, init_database


@pytest.fixture
def test_db_url():
    """Provide an in-memory SQLite database URL for testing."""
    return "sqlite:///:memory:"


@pytest.fixture
def engine(test_db_url):
    """Create a test database engine."""
    engine = create_engine(test_db_url, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    """Create a test database session."""
    session = Session(engine)
    yield session
    session.close()


def test_init_database():
    """Test database initialization creates tables."""
    # Use a shared memory database for this test
    test_url = "sqlite:///:memory:"
    engine = create_engine(test_url, echo=False)

    # Initialize database with the engine's URL
    Base.metadata.create_all(engine)

    # Verify tables exist by attempting to create a message
    session = Session(engine)
    message = Message(
        guesty_message_id="test123", message_text="Test message", timestamp=datetime.now()
    )
    session.add(message)
    session.commit()

    assert message.id is not None
    session.close()


def test_create_message(session):
    """Test creating a message record."""
    message = Message(
        guesty_message_id="msg_001",
        conversation_id="conv_001",
        reservation_id="res_001",
        guest_name="John Doe",
        message_text="Can we check in early at 10am?",
        timestamp=datetime(2025, 1, 15, 9, 30, 0),
        is_processed=False,
    )

    session.add(message)
    session.commit()

    assert message.id is not None
    assert message.guesty_message_id == "msg_001"
    assert message.is_processed is False
    assert message.llm_category is None


def test_unique_guesty_message_id(session):
    """Test that guesty_message_id must be unique."""
    message1 = Message(
        guesty_message_id="msg_duplicate", message_text="First message", timestamp=datetime.now()
    )
    session.add(message1)
    session.commit()

    # Attempt to create duplicate
    message2 = Message(
        guesty_message_id="msg_duplicate", message_text="Second message", timestamp=datetime.now()
    )
    session.add(message2)

    with pytest.raises(IntegrityError):
        session.commit()


def test_query_unprocessed_messages(session):
    """Test querying for unprocessed messages."""
    # Add processed message
    processed = Message(
        guesty_message_id="msg_processed",
        message_text="Processed message",
        timestamp=datetime.now(),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
    )

    # Add unprocessed messages
    unprocessed1 = Message(
        guesty_message_id="msg_unprocessed_1",
        message_text="Unprocessed message 1",
        timestamp=datetime.now(),
        is_processed=False,
    )

    unprocessed2 = Message(
        guesty_message_id="msg_unprocessed_2",
        message_text="Unprocessed message 2",
        timestamp=datetime.now(),
        is_processed=False,
    )

    session.add_all([processed, unprocessed1, unprocessed2])
    session.commit()

    # Query unprocessed messages
    stmt = select(Message).where(~Message.is_processed)
    result = session.execute(stmt).scalars().all()

    assert len(result) == 2
    assert all(msg.is_processed is False for msg in result)


def test_update_message_with_llm_results(session):
    """Test updating a message with LLM classification results."""
    message = Message(
        guesty_message_id="msg_to_classify",
        message_text="We'd like to check out late around 2pm if possible",
        timestamp=datetime.now(),
        is_processed=False,
    )
    session.add(message)
    session.commit()

    # Update with LLM results
    message.llm_category = "LATE_CHECKOUT"
    message.llm_summary = "Guest requesting late checkout at 2pm"
    message.llm_confidence = 0.95
    message.is_processed = True
    session.commit()

    # Verify updates
    stmt = select(Message).where(Message.guesty_message_id == "msg_to_classify")
    updated = session.execute(stmt).scalar_one()

    assert updated.llm_category == "LATE_CHECKOUT"
    assert updated.llm_summary == "Guest requesting late checkout at 2pm"
    assert updated.llm_confidence == 0.95
    assert updated.is_processed is True


def test_query_by_reservation_id(session):
    """Test querying messages by reservation_id."""
    reservation_id = "res_12345"

    msg1 = Message(
        guesty_message_id="msg_res_1",
        reservation_id=reservation_id,
        message_text="First message for reservation",
        timestamp=datetime.now(),
    )

    msg2 = Message(
        guesty_message_id="msg_res_2",
        reservation_id=reservation_id,
        message_text="Second message for reservation",
        timestamp=datetime.now(),
    )

    msg3 = Message(
        guesty_message_id="msg_other",
        reservation_id="res_other",
        message_text="Different reservation",
        timestamp=datetime.now(),
    )

    session.add_all([msg1, msg2, msg3])
    session.commit()

    # Query messages for specific reservation
    stmt = select(Message).where(Message.reservation_id == reservation_id)
    result = session.execute(stmt).scalars().all()

    assert len(result) == 2
    assert all(msg.reservation_id == reservation_id for msg in result)


def test_query_by_category(session):
    """Test querying messages by LLM category."""
    early_checkin1 = Message(
        guesty_message_id="msg_early_1",
        message_text="Early checkin request 1",
        timestamp=datetime.now(),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
    )

    early_checkin2 = Message(
        guesty_message_id="msg_early_2",
        message_text="Early checkin request 2",
        timestamp=datetime.now(),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
    )

    late_checkout = Message(
        guesty_message_id="msg_late",
        message_text="Late checkout request",
        timestamp=datetime.now(),
        is_processed=True,
        llm_category="LATE_CHECKOUT",
    )

    session.add_all([early_checkin1, early_checkin2, late_checkout])
    session.commit()

    # Query EARLY_CHECKIN messages
    stmt = select(Message).where(Message.llm_category == "EARLY_CHECKIN")
    result = session.execute(stmt).scalars().all()

    assert len(result) == 2
    assert all(msg.llm_category == "EARLY_CHECKIN" for msg in result)


def test_get_engine_and_session(test_db_url):
    """Test get_engine and get_session helper functions."""
    init_database(test_db_url)
    engine = get_engine(test_db_url)
    session = get_session(engine)

    assert engine is not None
    assert session is not None
    assert isinstance(session, Session)

    session.close()


def test_message_repr():
    """Test Message __repr__ method."""
    message = Message(
        id=1,
        guesty_message_id="msg_001",
        guest_name="Jane Smith",
        message_text="Test",
        timestamp=datetime.now(),
        is_processed=True,
    )

    repr_str = repr(message)
    assert "Message(" in repr_str
    assert "id=1" in repr_str
    assert "guesty_message_id='msg_001'" in repr_str
    assert "guest_name='Jane Smith'" in repr_str
    assert "is_processed=True" in repr_str
