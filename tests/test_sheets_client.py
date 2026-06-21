from unittest.mock import MagicMock, patch
import pytest


def _make_session(session_id="cs_live_abc", email="user@example.com", amount_total=1999, payment_intent="pi_abc"):
    session = MagicMock()
    session.id = session_id
    session.customer_email = email
    session.amount_total = amount_total
    session.payment_intent = payment_intent
    return session


@patch("sheets_client._gc")
@patch("sheets_client.config")
def test_append_row_calls_worksheet_append(mock_config, mock_gc):
    mock_config.GOOGLE_SPREADSHEET_ID = "sheet_id"
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["#", "Email"]]  # header only → row_number=1
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws
    mock_gc.open_by_key.return_value = mock_spreadsheet

    import sheets_client
    session = _make_session()
    sheets_client.append_row(session, "Pro Plan", "LT", 0.59, 1750000000)

    mock_ws.append_row.assert_called_once_with([
        1,
        "user@example.com",
        19.99,
        "Pro Plan",
        "LT",
        pytest.approx(19.40),
        "cs_live_abc",
        "pi_abc",
    ])


@patch("sheets_client._gc")
@patch("sheets_client.config")
def test_append_row_creates_sheet_tab_when_missing(mock_config, mock_gc):
    import gspread
    import sheets_client

    mock_config.GOOGLE_SPREADSHEET_ID = "sheet_id"
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["#", "Email", "Amount", "Product", "Country", "Net", "Session ID", "Payment Intent ID"]]
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_ws
    mock_gc.open_by_key.return_value = mock_spreadsheet

    session = _make_session()
    sheets_client.append_row(session, "Pro Plan", "LT", 0.59, 1750000000)

    mock_spreadsheet.add_worksheet.assert_called_once()
    mock_ws.append_row.assert_called()


@patch("sheets_client._gc")
@patch("sheets_client.config")
def test_append_row_swallows_exception(mock_config, mock_gc):
    import sheets_client

    mock_config.GOOGLE_SPREADSHEET_ID = "sheet_id"
    mock_gc.open_by_key.side_effect = Exception("network error")

    session = _make_session()
    # Must not raise
    sheets_client.append_row(session, "Pro Plan", "LT", 0.59, 1750000000)


@patch("sheets_client._gc")
@patch("sheets_client.config")
def test_append_row_empty_net_when_fee_is_none(mock_config, mock_gc):
    import sheets_client

    mock_config.GOOGLE_SPREADSHEET_ID = "sheet_id"
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["#"]]
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws
    mock_gc.open_by_key.return_value = mock_spreadsheet

    session = _make_session()
    sheets_client.append_row(session, None, None, None, 1750000000)

    args = mock_ws.append_row.call_args[0][0]
    assert args[5] == ""   # net is empty
    assert args[3] == ""   # product is empty
    assert args[4] == ""   # country is empty
