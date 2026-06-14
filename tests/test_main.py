# tests/test_main.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch, call
import main


def _make_event(event_id: str, created: int, user_id: str = "uid_abc") -> MagicMock:
    event = MagicMock()
    event.id = event_id
    event.created = created
    event.data.object.customer_email = "user@example.com"
    event.data.object.amount_total = 4900
    event.data.object.currency = "usd"
    event.data.object.metadata = {"user_id": user_id}
    return event


def test_poll_cycle_processes_new_event():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = False

    user = {"created_at": "2025-01-15T10:00:00"}

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.supabase_client.get_user", return_value=user), \
         patch("main.telegram_client.send_message") as mock_send, \
         patch("main.message_formatter.format_message", return_value="msg") as mock_fmt:
        main.run_poll_cycle(mock_state)

    mock_fmt.assert_called_once_with(event.data.object, user, 1700000100, mock_state.add_revenue.return_value)
    mock_send.assert_called_once_with("msg")
    mock_state.mark_processed.assert_called_once_with("evt_1")
    mock_state.set_last_event_created.assert_called_once_with(1700000100)


def test_poll_cycle_skips_already_processed_event():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = True

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.telegram_client.send_message") as mock_send:
        main.run_poll_cycle(mock_state)

    mock_send.assert_not_called()


def test_poll_cycle_continues_on_exception():
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000

    with patch("main.stripe_client.fetch_new_events", side_effect=Exception("boom")):
        # Should not raise
        main.run_poll_cycle(mock_state)


def test_poll_cycle_no_user_still_sends():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = False

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.supabase_client.get_user", return_value=None), \
         patch("main.telegram_client.send_message") as mock_send, \
         patch("main.message_formatter.format_message", return_value="msg"):
        main.run_poll_cycle(mock_state)

    mock_send.assert_called_once_with("msg")
