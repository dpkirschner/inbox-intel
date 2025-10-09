"""Tests for the report generation module."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.database import Message, get_engine, get_session
from src.reporter import (
    _get_arrivals_for_date,
    _get_messages_for_reservation,
    generate_daily_summary,
)


@pytest.fixture
def mock_client():
    """Create a mock GuestyClient."""
    with patch("src.reporter.GuestyClient") as mock:
        yield mock.return_value


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    from src.database import Base

    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = get_session(engine)
    yield session
    session.close()


def test_get_arrivals_for_date_success(mock_client):
    """Test fetching arrivals for a specific date."""
    target_date = date(2025, 5, 10)

    mock_response = {
        "results": [
            {
                "_id": "res_123",
                "guest": {"fullName": "Sarah P."},
                "listing": {"title": "Sunny Cottage"},
                "checkIn": "2025-05-10T15:00:00Z",
                "checkOut": "2025-05-12T11:00:00Z",
                "nightsCount": 2,
                "guestsCount": 2,
            }
        ]
    }

    mock_client.get_reservations.return_value = mock_response

    results = _get_arrivals_for_date(mock_client, target_date)

    assert len(results) == 1
    assert results[0]["_id"] == "res_123"
    assert results[0]["guest"]["fullName"] == "Sarah P."

    call_args = mock_client.get_reservations.call_args
    assert call_args[1]["checkin_from"] is not None
    assert call_args[1]["checkin_to"] is not None
    assert call_args[1]["limit"] == 100


def test_get_arrivals_for_date_no_results(mock_client):
    """Test fetching arrivals when no reservations exist."""
    target_date = date(2025, 5, 10)
    mock_client.get_reservations.return_value = {"results": []}

    results = _get_arrivals_for_date(mock_client, target_date)

    assert len(results) == 0


def test_get_messages_for_reservation(test_db):
    """Test fetching messages for a reservation."""
    message1 = Message(
        guesty_message_id="msg_1",
        reservation_id="res_123",
        message_text="Can we check in early?",
        timestamp=datetime.now(UTC),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
        llm_summary="Guest requests early check-in",
        llm_confidence=0.95,
    )

    message2 = Message(
        guesty_message_id="msg_2",
        reservation_id="res_123",
        message_text="We need extra towels",
        timestamp=datetime.now(UTC),
        is_processed=True,
        llm_category="SPECIAL_REQUEST",
        llm_summary="Guest needs extra towels",
        llm_confidence=0.88,
    )

    message3 = Message(
        guesty_message_id="msg_3",
        reservation_id="res_999",
        message_text="Different reservation",
        timestamp=datetime.now(UTC),
        is_processed=True,
        llm_category="GENERAL_QUESTION",
    )

    test_db.add_all([message1, message2, message3])
    test_db.commit()

    messages = _get_messages_for_reservation(test_db, "res_123")

    assert len(messages) == 2
    assert all(msg.reservation_id == "res_123" for msg in messages)
    assert messages[0].guesty_message_id == "msg_1"
    assert messages[1].guesty_message_id == "msg_2"


def test_get_messages_excludes_unprocessed(test_db):
    """Test that unprocessed messages are excluded."""
    message1 = Message(
        guesty_message_id="msg_1",
        reservation_id="res_123",
        message_text="Processed message",
        timestamp=datetime.now(UTC),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
    )

    message2 = Message(
        guesty_message_id="msg_2",
        reservation_id="res_123",
        message_text="Unprocessed message",
        timestamp=datetime.now(UTC),
        is_processed=False,
    )

    test_db.add_all([message1, message2])
    test_db.commit()

    messages = _get_messages_for_reservation(test_db, "res_123")

    assert len(messages) == 1
    assert messages[0].guesty_message_id == "msg_1"


@patch("src.reporter.get_session")
@patch("src.reporter.get_engine")
def test_generate_daily_summary_with_arrivals(
    mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test generating daily summary with arrivals and requests."""
    mock_get_session.return_value = test_db

    target_date = date(2025, 5, 10)

    mock_client.get_reservations.return_value = {
        "results": [
            {
                "_id": "res_123",
                "guest": {"fullName": "Sarah P."},
                "listing": {"title": "Sunny Cottage"},
                "checkIn": "2025-05-10T15:00:00Z",
                "checkOut": "2025-05-12T11:00:00Z",
                "nightsCount": 2,
                "guestsCount": 2,
            }
        ]
    }

    message = Message(
        guesty_message_id="msg_1",
        reservation_id="res_123",
        message_text="Can we check in at 10am?",
        timestamp=datetime.now(UTC),
        is_processed=True,
        llm_category="EARLY_CHECKIN",
        llm_summary="Guest requests early check-in at 10am",
        llm_confidence=0.95,
    )
    test_db.add(message)
    test_db.commit()

    with patch("src.reporter.GuestyClient", return_value=mock_client):
        summary = generate_daily_summary(target_date)

    assert "Daily Summary (May 10, 2025)" in summary
    assert "Sarah P." in summary
    assert "Sunny Cottage" in summary
    assert "Early Checkin" in summary
    assert "Guest requests early check-in at 10am" in summary
    assert "2 guests, 2 nights" in summary


@patch("src.reporter.get_session")
@patch("src.reporter.get_engine")
def test_generate_daily_summary_no_arrivals(
    mock_get_engine, mock_get_session, mock_client
):
    """Test generating daily summary with no arrivals."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    target_date = date(2025, 5, 10)

    mock_client.get_reservations.return_value = {"results": []}

    with patch("src.reporter.GuestyClient", return_value=mock_client):
        summary = generate_daily_summary(target_date)

    assert "Daily Summary (May 10, 2025)" in summary
    assert "No arrivals scheduled for today" in summary


@patch("src.reporter.get_session")
@patch("src.reporter.get_engine")
def test_generate_daily_summary_no_requests(
    mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test generating summary when arrivals have no special requests."""
    mock_get_session.return_value = test_db

    target_date = date(2025, 5, 10)

    mock_client.get_reservations.return_value = {
        "results": [
            {
                "_id": "res_456",
                "guest": {"firstName": "Tom", "lastName": "R."},
                "listing": {"nickname": "The Loft"},
                "checkIn": "2025-05-10T15:00:00Z",
                "nightsCount": 3,
                "guestsCount": 4,
            }
        ]
    }

    with patch("src.reporter.GuestyClient", return_value=mock_client):
        summary = generate_daily_summary(target_date)

    assert "Tom R." in summary
    assert "The Loft" in summary
    assert "No special requests noted" in summary
    assert "4 guests, 3 nights" in summary


@patch("src.reporter.get_session")
@patch("src.reporter.get_engine")
def test_generate_daily_summary_defaults_to_today(
    mock_get_engine, mock_get_session, mock_client
):
    """Test that summary defaults to today when no date provided."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    mock_client.get_reservations.return_value = {"results": []}

    with patch("src.reporter.GuestyClient", return_value=mock_client):
        summary = generate_daily_summary()

    today_str = date.today().strftime("%B %d, %Y")
    assert today_str in summary
