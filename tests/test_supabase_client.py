# tests/test_supabase_client.py
from unittest.mock import MagicMock, patch
import supabase_client


def _mock_admin_user(uid, email, created_at):
    user = MagicMock()
    user.id = uid
    user.email = email
    user.created_at = created_at
    resp = MagicMock()
    resp.user = user
    return resp


def test_get_user_returns_user_dict_when_found():
    mock_resp = _mock_admin_user("uid_abc", "user@example.com", "2025-01-15T10:00:00")

    with patch("supabase_client._client") as mock_client:
        mock_client.auth.admin.get_user_by_id.return_value = mock_resp
        result = supabase_client.get_user("uid_abc")

    assert result == {"id": "uid_abc", "email": "user@example.com", "created_at": "2025-01-15T10:00:00"}


def test_get_user_returns_none_when_not_found():
    mock_resp = MagicMock()
    mock_resp.user = None

    with patch("supabase_client._client") as mock_client:
        mock_client.auth.admin.get_user_by_id.return_value = mock_resp
        result = supabase_client.get_user("uid_missing")

    assert result is None


def test_get_user_returns_none_on_exception():
    with patch("supabase_client._client") as mock_client:
        mock_client.auth.admin.get_user_by_id.side_effect = Exception("Auth error")
        result = supabase_client.get_user("uid_abc")

    assert result is None


def test_get_purchase_country_returns_country_when_found():
    mock_response = MagicMock()
    mock_response.data = [{"buyer_country": "LT"}]

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_purchase_country("cs_live_abc")

    assert result == "LT"


def test_get_purchase_country_returns_none_when_not_found():
    mock_response = MagicMock()
    mock_response.data = []

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_purchase_country("cs_live_missing")

    assert result is None


def test_get_purchase_country_returns_none_on_exception():
    with patch("supabase_client._client") as mock_client:
        mock_client.table.side_effect = Exception("DB error")
        result = supabase_client.get_purchase_country("cs_live_err")

    assert result is None
