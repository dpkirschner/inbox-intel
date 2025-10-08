"""Tests for background worker module."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.database import Message, get_engine, get_session
from src.llm_classifier import ClassificationResult
from src.worker import _send_classification_alert, _should_send_alert, process_unclassified_messages


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

    def test_send_alert_for_alertable_category(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_alert",
            message_text="Can we check in early at 10am?",
            guest_name="John Doe",
            reservation_id="res_123",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add(message)
        session.commit()
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
            patch("src.worker.send_pushover_alert") as mock_alert,
            patch("src.worker.config") as mock_config,
        ):
            mock_get_engine.return_value = test_db_engine
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN", "MAINTENANCE_ISSUE"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            mock_classify.return_value = ClassificationResult(
                category="EARLY_CHECKIN",
                confidence=0.95,
                summary="Guest wants early check-in at 10am",
            )

            process_unclassified_messages()

            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            assert "Early Checkin" in call_args[0][0]
            assert "John Doe" in call_args[0][1]
            assert "95%" in call_args[0][1]

    def test_no_alert_for_non_alertable_category(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_no_alert",
            message_text="What time is checkout?",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add(message)
        session.commit()
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
            patch("src.worker.send_pushover_alert") as mock_alert,
            patch("src.worker.config") as mock_config,
        ):
            mock_get_engine.return_value = test_db_engine
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN", "MAINTENANCE_ISSUE"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            mock_classify.return_value = ClassificationResult(
                category="GENERAL_QUESTION",
                confidence=0.92,
                summary="Guest asking about checkout time",
            )

            process_unclassified_messages()

            mock_alert.assert_not_called()

    def test_no_alert_for_low_confidence(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_low_conf",
            message_text="Maybe early checkin?",
            timestamp=datetime.utcnow(),
            is_processed=False,
        )
        session.add(message)
        session.commit()
        session.close()

        with (
            patch("src.worker.get_engine") as mock_get_engine,
            patch("src.worker.classify_message") as mock_classify,
            patch("src.worker.send_pushover_alert") as mock_alert,
            patch("src.worker.config") as mock_config,
        ):
            mock_get_engine.return_value = test_db_engine
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            mock_classify.return_value = ClassificationResult(
                category="EARLY_CHECKIN",
                confidence=0.65,
                summary="Possible early check-in request",
            )

            process_unclassified_messages()

            mock_alert.assert_not_called()

    def test_alert_failure_does_not_stop_processing(self, test_db_engine):
        session = get_session(test_db_engine)
        message = Message(
            guesty_message_id="msg_alert_fail",
            message_text="Can we check in early?",
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
            patch("src.worker.send_pushover_alert") as mock_alert,
            patch("src.worker.config") as mock_config,
        ):
            mock_get_engine.return_value = test_db_engine
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            mock_classify.return_value = ClassificationResult(
                category="EARLY_CHECKIN",
                confidence=0.95,
                summary="Early check-in request",
            )

            from src.notifications import PushoverError

            mock_alert.side_effect = PushoverError("API error")

            processed_count = process_unclassified_messages()

            assert processed_count == 1

            verify_session = get_session(test_db_engine)
            message = verify_session.get(Message, msg_id)
            assert message.is_processed is True
            verify_session.close()


class TestShouldSendAlert:
    def test_should_send_alert_true(self):
        with patch("src.worker.config") as mock_config:
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN", "MAINTENANCE_ISSUE"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            assert _should_send_alert("EARLY_CHECKIN", 0.95) is True
            assert _should_send_alert("MAINTENANCE_ISSUE", 0.7) is True

    def test_should_send_alert_false_category(self):
        with patch("src.worker.config") as mock_config:
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            assert _should_send_alert("GENERAL_QUESTION", 0.95) is False

    def test_should_send_alert_false_confidence(self):
        with patch("src.worker.config") as mock_config:
            mock_config.ALERT_CATEGORIES = ["EARLY_CHECKIN"]
            mock_config.MIN_CONFIDENCE_THRESHOLD = 0.7

            assert _should_send_alert("EARLY_CHECKIN", 0.65) is False


class TestSendClassificationAlert:
    def test_send_alert_with_guest_name(self):
        message = Message(
            id=1,
            guesty_message_id="msg_123",
            guest_name="Jane Smith",
            reservation_id="res_456",
            message_text="Test",
            timestamp=datetime.utcnow(),
        )
        result = ClassificationResult(
            category="EARLY_CHECKIN",
            confidence=0.92,
            summary="Guest wants early check-in",
        )

        with patch("src.worker.send_pushover_alert") as mock_alert:
            _send_classification_alert(message, result)

            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[0]
            title = call_args[0]
            body = call_args[1]

            assert "Early Checkin" in title
            assert "Jane Smith" in body
            assert "92%" in body
            assert "Guest wants early check-in" in body
            assert "res_456" in body

    def test_send_alert_without_guest_name(self):
        message = Message(
            id=2,
            guesty_message_id="msg_456",
            guest_name=None,
            reservation_id=None,
            message_text="Test",
            timestamp=datetime.utcnow(),
        )
        result = ClassificationResult(
            category="MAINTENANCE_ISSUE",
            confidence=0.88,
            summary="WiFi not working",
        )

        with patch("src.worker.send_pushover_alert") as mock_alert:
            _send_classification_alert(message, result)

            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[0]
            title = call_args[0]
            body = call_args[1]

            assert "Maintenance Issue" in title
            assert "Unknown" in body
            assert "N/A" in body

    def test_send_alert_handles_pushover_error(self):
        message = Message(
            id=3,
            guesty_message_id="msg_789",
            guest_name="Test User",
            message_text="Test",
            timestamp=datetime.utcnow(),
        )
        result = ClassificationResult(
            category="EARLY_CHECKIN", confidence=0.90, summary="Test"
        )

        from src.notifications import PushoverError

        with patch("src.worker.send_pushover_alert") as mock_alert:
            mock_alert.side_effect = PushoverError("Failed to send")

            _send_classification_alert(message, result)
