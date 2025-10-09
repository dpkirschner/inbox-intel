"""Tests for historical backfill script."""

from datetime import UTC, datetime
from io import StringIO
from unittest.mock import MagicMock, call, patch

import pytest

from src.backfill import backfill_messages, main
from src.database import Message, get_engine, get_session


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    from src.database import Base

    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = get_session(engine)
    yield session
    session.close()


@pytest.fixture
def mock_client():
    """Create a mock GuestyClient."""
    with patch("src.backfill.GuestyClient") as mock:
        yield mock.return_value


@pytest.fixture
def sample_messages():
    """Sample message data from Guesty API."""
    return [
        {
            "_id": "msg_1",
            "body": "Early check-in request",
            "createdAt": "2025-01-01T10:00:00Z",
            "conversationId": "conv_1",
            "reservationId": "res_1",
            "from": "John Doe",
        },
        {
            "_id": "msg_2",
            "body": "Need extra towels",
            "createdAt": "2025-01-02T14:30:00Z",
            "conversationId": "conv_2",
            "reservationId": "res_2",
            "from": "Jane Smith",
        },
    ]


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_success(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db, sample_messages
):
    """Test successful backfill of messages."""
    mock_get_session.return_value = test_db

    mock_client._make_request.return_value = {
        "results": sample_messages,
        "count": 2,
    }

    stats = backfill_messages(days=7)

    assert stats["total_fetched"] == 2
    assert stats["new_saved"] == 2
    assert stats["duplicates_skipped"] == 0

    messages = test_db.query(Message).all()
    assert len(messages) == 2
    assert messages[0].guesty_message_id == "msg_1"
    assert messages[1].guesty_message_id == "msg_2"


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_with_duplicates(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db, sample_messages
):
    """Test backfill handles duplicate messages correctly."""
    mock_get_session.return_value = test_db

    existing_message = Message(
        guesty_message_id="msg_1",
        message_text="Existing message",
        timestamp=datetime.now(UTC),
        is_processed=False,
    )
    test_db.add(existing_message)
    test_db.commit()

    mock_client._make_request.return_value = {
        "results": sample_messages,
        "count": 2,
    }

    stats = backfill_messages(days=7)

    assert stats["total_fetched"] == 2
    assert stats["new_saved"] == 1
    assert stats["duplicates_skipped"] == 1


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_pagination(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test backfill handles pagination correctly."""
    mock_get_session.return_value = test_db

    batch1 = [
        {
            "_id": f"msg_{i}",
            "body": f"Message {i}",
            "createdAt": "2025-01-01T10:00:00Z",
        }
        for i in range(100)
    ]

    batch2 = [
        {
            "_id": f"msg_{i}",
            "body": f"Message {i}",
            "createdAt": "2025-01-01T10:00:00Z",
        }
        for i in range(100, 150)
    ]

    mock_client._make_request.side_effect = [
        {"results": batch1, "count": 150},
        {"results": batch2, "count": 150},
    ]

    stats = backfill_messages(days=30)

    assert stats["total_fetched"] == 150
    assert stats["new_saved"] == 150
    assert mock_client._make_request.call_count == 2


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_empty_response(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test backfill handles empty API response."""
    mock_get_session.return_value = test_db

    mock_client._make_request.return_value = {
        "results": [],
        "count": 0,
    }

    stats = backfill_messages(days=7)

    assert stats["total_fetched"] == 0
    assert stats["new_saved"] == 0
    assert stats["duplicates_skipped"] == 0


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_skips_invalid_messages(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test backfill skips messages without required fields."""
    mock_get_session.return_value = test_db

    messages = [
        {"_id": "msg_1", "body": "Valid message", "createdAt": "2025-01-01T10:00:00Z"},
        {"body": "Missing ID", "createdAt": "2025-01-01T10:00:00Z"},
        {"_id": "msg_3", "body": "Another valid", "createdAt": "2025-01-01T10:00:00Z"},
    ]

    mock_client._make_request.return_value = {
        "results": messages,
        "count": 3,
    }

    stats = backfill_messages(days=7)

    assert stats["total_fetched"] == 2
    assert stats["new_saved"] == 2


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_handles_timestamp_parsing_errors(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test backfill handles invalid timestamp formats."""
    mock_get_session.return_value = test_db

    messages = [
        {"_id": "msg_1", "body": "Message", "createdAt": "invalid-timestamp"},
    ]

    mock_client._make_request.return_value = {
        "results": messages,
        "count": 1,
    }

    stats = backfill_messages(days=7)

    assert stats["total_fetched"] == 1
    assert stats["new_saved"] == 1


def test_backfill_messages_invalid_days():
    """Test backfill raises error for invalid days parameter."""
    with pytest.raises(ValueError, match="Days must be a positive integer"):
        backfill_messages(days=0)

    with pytest.raises(ValueError, match="Days must be a positive integer"):
        backfill_messages(days=-1)


@patch("src.backfill.get_session")
@patch("src.backfill.get_engine")
@patch("src.backfill.init_database")
def test_backfill_messages_api_error_propagates(
    mock_init_db, mock_get_engine, mock_get_session, mock_client, test_db
):
    """Test that API errors are propagated."""
    mock_get_session.return_value = test_db
    mock_client._make_request.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        backfill_messages(days=7)


@patch("src.backfill.backfill_messages")
def test_main_default_days(mock_backfill):
    """Test main function with default days from config."""
    mock_backfill.return_value = {
        "total_fetched": 10,
        "new_saved": 8,
        "duplicates_skipped": 2,
    }

    with patch("sys.argv", ["backfill.py"]):
        exit_code = main()

    assert exit_code == 0
    mock_backfill.assert_called_once()


@patch("src.backfill.backfill_messages")
def test_main_custom_days(mock_backfill):
    """Test main function with custom days argument."""
    mock_backfill.return_value = {
        "total_fetched": 50,
        "new_saved": 50,
        "duplicates_skipped": 0,
    }

    with patch("sys.argv", ["backfill.py", "--days", "30"]):
        exit_code = main()

    assert exit_code == 0
    mock_backfill.assert_called_once_with(30)


@patch("src.backfill.backfill_messages")
def test_main_handles_value_error(mock_backfill):
    """Test main function handles ValueError gracefully."""
    mock_backfill.side_effect = ValueError("Invalid days")

    with patch("sys.argv", ["backfill.py", "--days", "30"]):
        exit_code = main()

    assert exit_code == 1


@patch("src.backfill.backfill_messages")
def test_main_handles_general_error(mock_backfill):
    """Test main function handles general exceptions."""
    mock_backfill.side_effect = Exception("API error")

    with patch("sys.argv", ["backfill.py", "--days", "7"]):
        exit_code = main()

    assert exit_code == 1


@patch("src.backfill.backfill_messages")
@patch("sys.stdout", new_callable=StringIO)
def test_main_prints_statistics(mock_stdout, mock_backfill):
    """Test main function prints statistics correctly."""
    mock_backfill.return_value = {
        "total_fetched": 100,
        "new_saved": 85,
        "duplicates_skipped": 15,
    }

    with patch("sys.argv", ["backfill.py"]):
        main()

    output = mock_stdout.getvalue()
    assert "BACKFILL COMPLETE" in output
    assert "Total messages fetched: 100" in output
    assert "New messages saved:     85" in output
    assert "Duplicates skipped:     15" in output
