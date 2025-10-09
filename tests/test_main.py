"""Tests for main module."""

from unittest.mock import patch

from src.main import _generate_and_log_daily_summary


@patch("src.main.send_daily_summary")
@patch("src.main.generate_daily_summary")
def test_generate_and_log_daily_summary_success(mock_generate, mock_send):
    """Test that daily summary is generated and sent successfully."""
    mock_generate.return_value = "Test summary"

    _generate_and_log_daily_summary()

    mock_generate.assert_called_once()
    mock_send.assert_called_once_with("Test summary")


@patch("src.main.send_daily_summary")
@patch("src.main.generate_daily_summary")
@patch("src.main.logger")
def test_generate_and_log_daily_summary_logs_output(
    mock_logger, mock_generate, mock_send
):
    """Test that summary output is logged."""
    test_summary = "📅 **Daily Summary**\n- Test content"
    mock_generate.return_value = test_summary

    _generate_and_log_daily_summary()

    mock_logger.info.assert_any_call("Generating daily summary report")
    mock_logger.info.assert_any_call(f"Daily Summary:\n{test_summary}")
    mock_send.assert_called_once_with(test_summary)


@patch("src.main.send_daily_summary")
@patch("src.main.generate_daily_summary")
@patch("src.main.logger")
def test_generate_and_log_daily_summary_handles_errors(
    mock_logger, mock_generate, mock_send
):
    """Test that errors in summary generation are handled gracefully."""
    mock_generate.side_effect = Exception("Test error")

    _generate_and_log_daily_summary()

    mock_logger.error.assert_called_once()
    assert "Failed to generate or send daily summary" in str(
        mock_logger.error.call_args
    )
    mock_send.assert_not_called()
