# tests/test_stripe_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch
import stripe_client


def _make_event(event_id: str, created: int, session_data: dict) -> MagicMock:
    event = MagicMock()
    event.id = event_id
    event.created = created
    event.data.object = MagicMock(**session_data)
    return event


def test_fetch_new_events_returns_list():
    mock_event = _make_event("evt_1", 1700000100, {
        "id": "cs_1",
        "customer_email": "user@example.com",
        "amount_total": 4900,
        "currency": "usd",
        "metadata": {"user_id": "uid_abc"},
    })

    with patch("stripe_client.stripe.Event.list") as mock_list:
        mock_list.return_value.auto_paging_iter.return_value = [mock_event]
        events = stripe_client.fetch_new_events(since_timestamp=1700000000)

    assert len(events) == 1
    assert events[0].id == "evt_1"
    mock_list.assert_called_once_with(
        type="checkout.session.completed",
        created={"gte": 1700000000},
    )


def test_fetch_new_events_returns_empty_list_when_none():
    with patch("stripe_client.stripe.Event.list") as mock_list:
        mock_list.return_value.auto_paging_iter.return_value = []
        events = stripe_client.fetch_new_events(since_timestamp=1700000000)

    assert events == []
