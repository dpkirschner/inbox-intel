"""Tests for message polling functionality."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.polling import fetch_and_save_messages


@pytest.fixture
def mock_guesty_messages_response():
    """Mock Guesty API messages response."""
    return {
        "results": [
            {
                "_id": "msg_001",
                "body": "Hi, we will arrive at 3pm tomorrow",
                "createdAt": "2024-01-15T15:30:00.000Z",
                "conversationId": "conv_001",
                "reservationId": "res_001",
                "from": "John Doe",
            },
            {
                "_id": "msg_002",
                "body": "Can we have early check-in?",
                "createdAt": "2024-01-15T15:35:00.000Z",
                "conversationId": "conv_001",
                "reservationId": "res_001",
                "from": "John Doe",
            },
            {
                "_id": "msg_003",
                "body": "Thank you for your message",
                "createdAt": "2024-01-15T15:40:00.000Z",
                "conversationId": "conv_002",
                "reservationId": "res_002",
                "from": "Jane Smith",
            },
        ],
        "count": 3,
    }


@pytest.fixture
def mock_empty_response():
    """Mock empty Guesty API response."""
    return {"results": [], "count": 0}


class TestFetchAndSaveMessages:
    """Tests for fetch_and_save_messages function."""

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_success(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
        mock_guesty_messages_response,
    ):
        """Test successfully fetching and saving messages."""
        mock_client = Mock()
        mock_client._make_request.return_value = mock_guesty_messages_response
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.side_effect = [Mock(), Mock(), Mock()]

        result = fetch_and_save_messages(minutes_lookback=5)

        assert result == 3
        assert mock_client._make_request.call_count == 1
        assert mock_save_message.call_count == 3
        mock_session.close.assert_called_once()

        call_args = mock_client._make_request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "communication/conversations/messages"
        assert "createdFrom" in call_args[1]["params"]
        assert call_args[1]["params"]["limit"] == 100
        assert call_args[1]["params"]["sort"] == "createdAt"

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_with_duplicates(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
        mock_guesty_messages_response,
    ):
        """Test fetching messages with some duplicates."""
        mock_client = Mock()
        mock_client._make_request.return_value = mock_guesty_messages_response
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.side_effect = [Mock(), None, Mock()]

        result = fetch_and_save_messages(minutes_lookback=5)

        assert result == 2
        assert mock_save_message.call_count == 3
        mock_session.close.assert_called_once()

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    def test_fetch_and_save_messages_empty_response(
        self,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
        mock_empty_response,
    ):
        """Test fetching when no new messages are available."""
        mock_client = Mock()
        mock_client._make_request.return_value = mock_empty_response
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        result = fetch_and_save_messages(minutes_lookback=5)

        assert result == 0
        mock_session.close.assert_called_once()

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_skips_invalid_messages(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
    ):
        """Test that messages without _id are skipped."""
        mock_client = Mock()
        mock_client._make_request.return_value = {
            "results": [
                {
                    "_id": "msg_001",
                    "body": "Valid message",
                    "createdAt": "2024-01-15T15:30:00.000Z",
                },
                {
                    "body": "Invalid message without _id",
                    "createdAt": "2024-01-15T15:35:00.000Z",
                },
                {
                    "_id": "msg_003",
                    "body": "Another valid message",
                    "createdAt": "2024-01-15T15:40:00.000Z",
                },
            ],
            "count": 3,
        }
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.side_effect = [Mock(), Mock()]

        result = fetch_and_save_messages(minutes_lookback=5)

        assert result == 2
        assert mock_save_message.call_count == 2

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_handles_timestamp_parsing_errors(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
    ):
        """Test handling of invalid timestamp formats."""
        mock_client = Mock()
        mock_client._make_request.return_value = {
            "results": [
                {
                    "_id": "msg_001",
                    "body": "Message with invalid timestamp",
                    "createdAt": "invalid-timestamp",
                },
            ],
            "count": 1,
        }
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.return_value = Mock()

        result = fetch_and_save_messages(minutes_lookback=5)

        assert result == 1
        assert mock_save_message.call_count == 1

        call_args = mock_save_message.call_args
        assert isinstance(call_args[1]["timestamp"], datetime)

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    def test_fetch_and_save_messages_handles_api_error(
        self,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
    ):
        """Test handling of API request errors."""
        mock_client = Mock()
        mock_client._make_request.side_effect = Exception("API connection failed")
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match="API connection failed"):
            fetch_and_save_messages(minutes_lookback=5)

        mock_session.close.assert_called_once()

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_custom_lookback(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
        mock_guesty_messages_response,
    ):
        """Test fetch_and_save_messages with custom lookback period."""
        mock_client = Mock()
        mock_client._make_request.return_value = mock_guesty_messages_response
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.side_effect = [Mock(), Mock(), Mock()]

        result = fetch_and_save_messages(minutes_lookback=15)

        assert result == 3

        call_args = mock_client._make_request.call_args
        params = call_args[1]["params"]
        assert "createdFrom" in params

        created_from = datetime.fromisoformat(params["createdFrom"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        time_diff = (now - created_from).total_seconds() / 60

        assert 14 < time_diff < 16

    @patch("src.polling.GuestyClient")
    @patch("src.polling.get_engine")
    @patch("src.polling.get_session")
    @patch("src.polling.save_message_from_webhook")
    def test_fetch_and_save_messages_saves_all_fields(
        self,
        mock_save_message,
        mock_get_session,
        mock_get_engine,
        mock_client_class,
    ):
        """Test that all message fields are passed to save function."""
        mock_client = Mock()
        mock_client._make_request.return_value = {
            "results": [
                {
                    "_id": "msg_001",
                    "body": "Test message",
                    "createdAt": "2024-01-15T15:30:00.000Z",
                    "conversationId": "conv_001",
                    "reservationId": "res_001",
                    "from": "John Doe",
                }
            ],
            "count": 1,
        }
        mock_client_class.return_value = mock_client

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        mock_save_message.return_value = Mock()

        fetch_and_save_messages(minutes_lookback=5)

        call_args = mock_save_message.call_args
        assert call_args[1]["message_id"] == "msg_001"
        assert call_args[1]["message_text"] == "Test message"
        assert call_args[1]["conversation_id"] == "conv_001"
        assert call_args[1]["reservation_id"] == "res_001"
        assert call_args[1]["guest_name"] == "John Doe"
        assert isinstance(call_args[1]["timestamp"], datetime)
