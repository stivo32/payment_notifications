# tests/test_message_formatter.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock
import message_formatter


def _make_session(email: str, amount_total: int, currency: str, metadata: dict) -> MagicMock:
    session = MagicMock()
    session.customer_email = email
    session.amount_total = amount_total
    session.currency = currency
    session.metadata = metadata
    return session


def test_format_with_user_data():
    session = _make_session("user@example.com", 4900, "usd", {"user_id": "uid_abc"})
    user = {"created_at": "2025-01-15T10:00:00", "email": "user@example.com"}
    result = message_formatter.format_message(session, user)

    assert "user@example.com" in result
    assert "$49.00" in result
    assert "2025-01-15" in result
    assert "⚠️" not in result


def test_format_without_user_data_adds_warning():
    session = _make_session("user@example.com", 4900, "usd", {})
    result = message_formatter.format_message(session, None)

    assert "user@example.com" in result
    assert "$49.00" in result
    assert "⚠️ User not found in DB" in result


def test_format_converts_cents_to_dollars():
    session = _make_session("a@b.com", 10050, "usd", {})
    result = message_formatter.format_message(session, None)
    assert "$100.50" in result


def test_format_currency_symbol():
    session = _make_session("a@b.com", 1000, "eur", {})
    result = message_formatter.format_message(session, None)
    assert "€10.00" in result
