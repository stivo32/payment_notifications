# tests/test_supabase_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch
import supabase_client


def test_get_user_returns_user_dict_when_found():
    mock_response = MagicMock()
    mock_response.data = [{"id": "uid_abc", "email": "user@example.com", "created_at": "2025-01-15T10:00:00"}]

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_user("uid_abc")

    assert result == {"id": "uid_abc", "email": "user@example.com", "created_at": "2025-01-15T10:00:00"}


def test_get_user_returns_none_when_not_found():
    mock_response = MagicMock()
    mock_response.data = []

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_user("uid_missing")

    assert result is None


def test_get_user_returns_none_on_exception():
    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        result = supabase_client.get_user("uid_abc")

    assert result is None
