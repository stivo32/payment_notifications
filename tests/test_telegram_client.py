# tests/test_telegram_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch, call
import pytest
import telegram_client


def test_send_message_succeeds_on_first_try():
    mock_response = MagicMock()
    mock_response.ok = True

    with patch("telegram_client.requests.post", return_value=mock_response) as mock_post:
        telegram_client.send_message("Hello")

    assert mock_post.call_count == 1


def test_send_message_retries_on_failure_then_succeeds():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "Bad Gateway"

    ok_response = MagicMock()
    ok_response.ok = True

    with patch("telegram_client.requests.post", side_effect=[fail_response, ok_response]) as mock_post:
        with patch("telegram_client.time.sleep"):
            telegram_client.send_message("Hello")

    assert mock_post.call_count == 2


def test_send_message_logs_error_after_all_retries_fail():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "Server Error"

    with patch("telegram_client.requests.post", return_value=fail_response):
        with patch("telegram_client.time.sleep"):
            with patch("telegram_client.logger") as mock_logger:
                telegram_client.send_message("Hello")

    mock_logger.error.assert_called_once()


def test_send_message_uses_exponential_backoff():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "err"

    with patch("telegram_client.requests.post", return_value=fail_response):
        with patch("telegram_client.time.sleep") as mock_sleep:
            telegram_client.send_message("Hello")

    assert mock_sleep.call_args_list == [call(1), call(2), call(4)]
