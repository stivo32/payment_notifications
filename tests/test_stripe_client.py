# tests/test_stripe_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch
import pytest
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


def test_fetch_product_name_returns_name():
    mock_price = MagicMock()
    mock_price.product.name = "Pro Plan"

    with patch("stripe_client.stripe.Price.retrieve", return_value=mock_price) as mock_retrieve:
        result = stripe_client.fetch_product_name("price_123")

    assert result == "Pro Plan"
    mock_retrieve.assert_called_once_with("price_123", expand=["product"])


def test_fetch_product_name_caches_result():
    mock_price = MagicMock()
    mock_price.product.name = "Pro Plan"

    # Clear cache before test
    stripe_client._price_name_cache.clear()

    with patch("stripe_client.stripe.Price.retrieve", return_value=mock_price) as mock_retrieve:
        stripe_client.fetch_product_name("price_cache_test")
        stripe_client.fetch_product_name("price_cache_test")

    mock_retrieve.assert_called_once()  # second call hits cache


def test_fetch_product_name_returns_price_id_on_error():
    stripe_client._price_name_cache.clear()

    with patch("stripe_client.stripe.Price.retrieve", side_effect=stripe_client.stripe.StripeError("fail")):
        result = stripe_client.fetch_product_name("price_err")

    assert result == "price_err"


def test_fetch_stripe_fee_returns_fee_in_major_units():
    mock_pi = MagicMock()
    mock_pi.latest_charge.balance_transaction.fee = 59  # cents

    with patch("stripe_client.stripe.PaymentIntent.retrieve", return_value=mock_pi) as mock_retrieve:
        result = stripe_client.fetch_stripe_fee("pi_123")

    assert result == pytest.approx(0.59)
    mock_retrieve.assert_called_once_with("pi_123", expand=["latest_charge.balance_transaction"])


def test_fetch_stripe_fee_returns_none_on_stripe_error():
    with patch("stripe_client.stripe.PaymentIntent.retrieve", side_effect=stripe_client.stripe.StripeError("fail")):
        result = stripe_client.fetch_stripe_fee("pi_err")

    assert result is None


def test_fetch_stripe_fee_returns_none_when_balance_transaction_missing():
    mock_pi = MagicMock()
    mock_pi.latest_charge.balance_transaction = None  # None.fee raises AttributeError

    with patch("stripe_client.stripe.PaymentIntent.retrieve", return_value=mock_pi):
        result = stripe_client.fetch_stripe_fee("pi_nobt")

    assert result is None
