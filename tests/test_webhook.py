"""Tests for webhook endpoint functionality."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database import Base, Message


@pytest.fixture
def test_db_url():
    """Provide a shared memory SQLite database URL for testing."""
    import uuid
    db_name = f"memdb{uuid.uuid4().hex}"
    return f"sqlite:///{db_name}?mode=memory&cache=shared&uri=true"


@pytest.fixture(scope="function")
def engine(test_db_url):
    """Create a test database engine."""
    engine = create_engine(
        test_db_url, echo=False, connect_args={"check_same_thread": False, "uri": True}
    )

    conn = engine.connect()
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    conn.close()
    engine.dispose()


@pytest.fixture
def session(engine):
    """Create a test database session."""
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def client(engine, monkeypatch):
    """Create a test client with dependency override for database."""
    from src import main

    # Set the global engine before lifespan runs
    main._engine = engine

    # Mock config to use in-memory database
    monkeypatch.setattr("src.main.config.DATABASE_URL", "sqlite:///:memory:")

    with TestClient(main.app) as test_client:
        yield test_client

    # Clean up
    main._engine = None
    main.app.dependency_overrides = {}


@pytest.fixture
def sample_webhook_payload():
    """Sample Guesty webhook payload for a received message."""
    return {
        "event": "reservation.messageReceived",
        "reservationId": "res_12345",
        "conversation": {"_id": "conv_67890"},
        "message": {
            "_id": "msg_abc123",
            "body": "Hi! Can we check in early at 10am?",
            "createdAt": "2025-01-15T09:30:00Z",
            "from": "guest@example.com",
            "to": "host@example.com",
            "type": "fromGuest",
        },
    }


class TestWebhookEndpoint:
    """Tests for the Guesty webhook endpoint."""

    def test_root_endpoint(self, client):
        """Test the root health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "InboxIntel"}

    def test_database_tables_exist(self, engine):
        """Test that database tables were created."""
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "messages" in tables

    def test_receive_valid_message_webhook(self, client, sample_webhook_payload):
        """Test receiving a valid message webhook."""
        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == "msg_abc123"
        assert data["is_duplicate"] is False

    def test_receive_duplicate_message(self, client, sample_webhook_payload):
        """Test that duplicate messages are detected and skipped."""
        response1 = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)
        assert response1.status_code == 200
        assert response1.json()["is_duplicate"] is False

        response2 = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)
        assert response2.status_code == 200
        assert response2.json()["is_duplicate"] is True

    def test_unsupported_event_type(self, client, sample_webhook_payload):
        """Test handling of unsupported event types."""
        sample_webhook_payload["event"] = "reservation.updated"

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 400
        assert "Unsupported event" in response.json()["detail"]

    def test_missing_message_field(self, client):
        """Test handling of payload missing message field."""
        payload = {"event": "reservation.messageReceived", "reservationId": "res_123"}

        response = client.post("/webhooks/guesty/messages", json=payload)

        assert response.status_code == 422

    def test_message_missing_id(self, client, sample_webhook_payload):
        """Test handling of message missing _id field."""
        del sample_webhook_payload["message"]["_id"]

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 400
        assert "missing '_id'" in response.json()["detail"]

    def test_message_with_empty_body(self, client, sample_webhook_payload):
        """Test handling of message with empty body."""
        sample_webhook_payload["message"]["body"] = ""

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_message_sent_event(self, client, sample_webhook_payload):
        """Test receiving a messageSent event."""
        sample_webhook_payload["event"] = "reservation.messageSent"
        sample_webhook_payload["message"]["_id"] = "msg_sent_001"
        sample_webhook_payload["message"]["type"] = "fromHost"

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_message_without_reservation_id(self, client, sample_webhook_payload):
        """Test handling message without reservation ID."""
        sample_webhook_payload["reservationId"] = None

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_message_without_conversation(self, client, sample_webhook_payload):
        """Test handling message without conversation object."""
        sample_webhook_payload["conversation"] = None

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_invalid_timestamp_format(self, client, sample_webhook_payload):
        """Test handling of invalid timestamp format."""
        sample_webhook_payload["message"]["createdAt"] = "invalid-timestamp"

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_missing_timestamp(self, client, sample_webhook_payload):
        """Test handling of missing timestamp field."""
        del sample_webhook_payload["message"]["createdAt"]

        response = client.post("/webhooks/guesty/messages", json=sample_webhook_payload)

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestDatabaseIntegration:
    """Tests for database save functionality from webhooks."""

    def test_save_message_from_webhook(self, session):
        """Test saving a message to the database."""
        from src.database import save_message_from_webhook

        message = save_message_from_webhook(
            session=session,
            message_id="msg_test_001",
            message_text="Test message content",
            timestamp=datetime(2025, 1, 15, 10, 0, 0),
            conversation_id="conv_001",
            reservation_id="res_001",
            guest_name="test@example.com",
        )

        assert message is not None
        assert message.guesty_message_id == "msg_test_001"
        assert message.message_text == "Test message content"
        assert message.is_processed is False

    def test_save_duplicate_message(self, session):
        """Test that duplicate messages are not saved."""
        from src.database import save_message_from_webhook

        message1 = save_message_from_webhook(
            session=session,
            message_id="msg_duplicate",
            message_text="First message",
            timestamp=datetime.now(),
        )

        message2 = save_message_from_webhook(
            session=session,
            message_id="msg_duplicate",
            message_text="Duplicate attempt",
            timestamp=datetime.now(),
        )

        assert message1 is not None
        assert message2 is None

        stmt = select(Message).where(Message.guesty_message_id == "msg_duplicate")
        result = session.execute(stmt).scalars().all()
        assert len(result) == 1

    def test_save_message_with_minimal_fields(self, session):
        """Test saving a message with only required fields."""
        from src.database import save_message_from_webhook

        message = save_message_from_webhook(
            session=session,
            message_id="msg_minimal",
            message_text="Minimal message",
            timestamp=datetime.now(),
        )

        assert message is not None
        assert message.conversation_id is None
        assert message.reservation_id is None
        assert message.guest_name is None
