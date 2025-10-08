"""Tests for background worker module."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.database import Message, get_engine, get_session
from src.llm_classifier import ClassificationResult
from src.worker import process_unclassified_messages


@pytest.fixture
def test_db_engine():
    from src.database import Base

    database_url = "sqlite:///:memory:"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)


class TestProcessUnclassifiedMessages:
    def test_process_no_messages(self, test_db_engine):
        with (
            patch("src.worker.config") as mock_config,
            patch("src.worker.get_engine") as mock_get_engine,
        ):
            mock_config.DATABASE_URL = "sqlite:///:memory:"
            mock_get_engine.return_value = test_db_engine

            processed_count = process_unclassified_messages()

            assert processed_count == 0

    def test_process_single_unclassified_message(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_123",
            message_text="Can we check in early at 10am?",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add(message)
        session.commit()
        message_id = message.id
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
        ):
            mock_get_engine.return_value = test_db_engine

            mock_classify.return_value = ClassificationResult(
                category="EARLY_CHECKIN",
                confidence=0.95,
                summary="Guest wants early check-in at 10am",
            )

            processed_count = process_unclassified_messages()

            assert processed_count == 1

            verify_session = get_session(test_db_engine)
            updated_message = verify_session.get(Message, message_id)
            assert updated_message.is_processed is True
            assert updated_message.llm_category == "EARLY_CHECKIN"
            assert updated_message.llm_confidence == 0.95
            assert updated_message.llm_summary == "Guest wants early check-in at 10am"
            verify_session.close()

            mock_classify.assert_called_once_with("Can we check in early at 10am?")

    def test_process_multiple_unclassified_messages(self, test_db_engine):
        session = get_session(test_db_engine)
        message1 = Message(
            guesty_message_id="msg_1",
            message_text="Can we check in early?",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        message2 = Message(
            guesty_message_id="msg_2",
            message_text="The WiFi is not working",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add_all([message1, message2])
        session.commit()
        msg1_id, msg2_id = message1.id, message2.id
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
        ):
            mock_get_engine.return_value = test_db_engine

            mock_classify.side_effect = [
                ClassificationResult(
                    category="EARLY_CHECKIN", confidence=0.90, summary="Early check-in request"
                ),
                ClassificationResult(
                    category="MAINTENANCE_ISSUE", confidence=0.98, summary="WiFi issue"
                ),
            ]

            processed_count = process_unclassified_messages()

            assert processed_count == 2

            verify_session = get_session(test_db_engine)
            message1 = verify_session.get(Message, msg1_id)
            message2 = verify_session.get(Message, msg2_id)

            assert message1.is_processed is True
            assert message1.llm_category == "EARLY_CHECKIN"
            assert message2.is_processed is True
            assert message2.llm_category == "MAINTENANCE_ISSUE"
            verify_session.close()

    def test_skip_already_processed_messages(self, test_db_engine):
        session = get_session(test_db_engine)
        processed_message = Message(
            guesty_message_id="msg_processed",
            message_text="Already processed",
            timestamp=datetime.utcnow(),
            is_processed=True,
            llm_category="GENERAL_QUESTION",
            llm_confidence=0.85,
        )
        unprocessed_message = Message(
            guesty_message_id="msg_unprocessed",
            message_text="Not processed yet",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add_all([processed_message, unprocessed_message])
        session.commit()
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
        ):
            mock_get_engine.return_value = test_db_engine

            mock_classify.return_value = ClassificationResult(
                category="SPECIAL_REQUEST", confidence=0.88, summary="Special request"
            )

            processed_count = process_unclassified_messages()

            assert processed_count == 1
            mock_classify.assert_called_once_with("Not processed yet")

    def test_handle_classification_error(self, test_db_engine):
        session = get_session(test_db_engine)
        message1 = Message(
            guesty_message_id="msg_1",
            message_text="Message 1",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        message2 = Message(
            guesty_message_id="msg_2",
            message_text="Message 2",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add_all([message1, message2])
        session.commit()
        msg1_id, msg2_id = message1.id, message2.id
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
        ):
            mock_get_engine.return_value = test_db_engine

            mock_classify.side_effect = [
                Exception("LLM API error"),
                ClassificationResult(
                    category="GENERAL_QUESTION", confidence=0.80, summary="Question"
                ),
            ]

            processed_count = process_unclassified_messages()

            assert processed_count == 1

            verify_session = get_session(test_db_engine)
            message1 = verify_session.get(Message, msg1_id)
            message2 = verify_session.get(Message, msg2_id)

            assert message1.is_processed is False
            assert message2.is_processed is True
            verify_session.close()

    def test_rollback_on_individual_failure(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_fail",
            message_text="This will fail",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add(message)
        session.commit()
        msg_id = message.id
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
        ):
            mock_get_engine.return_value = test_db_engine

            mock_classify.side_effect = ValueError("Classification failed")

            processed_count = process_unclassified_messages()

            assert processed_count == 0

            verify_session = get_session(test_db_engine)
            message = verify_session.get(Message, msg_id)
            assert message.is_processed is False
            assert message.llm_category is None
            verify_session.close()
