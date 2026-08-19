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

    from datetime import datetime, timezone
    expected_ts = datetime.fromtimestamp(1750000000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mock_ws.append_row.assert_called_once_with([
        1,
        expected_ts,
        "user@example.com",
        "Pro Plan",
        "LT",
        pytest.approx(19.99),
        pytest.approx(0.59),
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
    assert args[3] == ""   # product is empty
    assert args[4] == ""   # country is empty
    assert args[6] == ""   # fee is empty
    assert args[7] == ""   # net is empty


def test_get_or_create_summary_sheet_uses_existing():
    import sheets_client

    mock_spreadsheet = MagicMock()
    mock_summary_ws = MagicMock()
    mock_summary_ws.get_all_values.return_value = [
        ["Month", "Total Amount", "Total Net", "Stripe Fee"],
        ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"],
    ]
    mock_spreadsheet.worksheet.return_value = mock_summary_ws

    ws = sheets_client._get_or_create_summary_sheet(mock_spreadsheet)
    assert ws == mock_summary_ws
    mock_spreadsheet.worksheet.assert_called_once_with("Summary")
    mock_summary_ws.append_rows.assert_not_called()


def test_get_or_create_summary_sheet_renames_first_sheet_and_initializes():
    import gspread
    import sheets_client

    mock_spreadsheet = MagicMock()
    mock_first_ws = MagicMock()
    mock_first_ws.get_all_values.return_value = []
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound
    mock_spreadsheet.get_worksheet.return_value = mock_first_ws

    ws = sheets_client._get_or_create_summary_sheet(mock_spreadsheet)
    assert ws == mock_first_ws
    mock_first_ws.update_title.assert_called_once_with("Summary")
    mock_first_ws.append_rows.assert_called_once_with(
        [
            ["Month", "Total Amount", "Total Net", "Stripe Fee"],
            ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"],
        ],
        value_input_option="USER_ENTERED",
    )


def test_ensure_month_in_summary_appends_formula_row():
    import sheets_client

    mock_spreadsheet = MagicMock()
    mock_summary_ws = MagicMock()
    mock_summary_ws.get_all_values.return_value = [
        ["Month", "Total Amount", "Total Net", "Stripe Fee"],
        ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"],
        ["2024-05", "=SUM('2024-05'!F2:F)", "=SUM('2024-05'!H2:H)", "=SUM('2024-05'!G2:G)"],
    ]
    mock_summary_ws.col_values.return_value = ["Month", "Total", "2024-05"]
    mock_spreadsheet.worksheet.return_value = mock_summary_ws

    sheets_client._ensure_month_in_summary(mock_spreadsheet, "2024-06")

    mock_summary_ws.append_row.assert_called_once_with(
        ["2024-06", "=SUM('2024-06'!F2:F)", "=SUM('2024-06'!H2:H)", "=SUM('2024-06'!G2:G)"],
        value_input_option="USER_ENTERED",
    )


def test_ensure_month_in_summary_skips_when_month_exists():
    import sheets_client

    mock_spreadsheet = MagicMock()
    mock_summary_ws = MagicMock()
    mock_summary_ws.col_values.return_value = ["Month", "Total", "2024-06"]
    mock_spreadsheet.worksheet.return_value = mock_summary_ws

    sheets_client._ensure_month_in_summary(mock_spreadsheet, "2024-06")

    mock_summary_ws.append_row.assert_not_called()


@patch("sheets_client._ensure_month_in_summary")
def test_get_or_create_sheet_registers_month_in_summary_when_created(mock_ensure_summary):
    import gspread
    import sheets_client

    mock_spreadsheet = MagicMock()
    mock_ws = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_ws

    sheets_client._get_or_create_sheet(mock_spreadsheet, "2024-06")

    mock_ensure_summary.assert_called_once_with(mock_spreadsheet, "2024-06")


@patch("sheets_client._get_gc")
@patch("sheets_client.config")
def test_sync_summary_sheet_scans_and_adds_missing_month_tabs(mock_config, mock_get_gc):
    import sheets_client

    mock_config.GOOGLE_SPREADSHEET_ID = "sheet_id"
    mock_spreadsheet = MagicMock()
    mock_get_gc.return_value.open_by_key.return_value = mock_spreadsheet

    # Mock worksheets: Summary, 2024-07, 2024-05, other_tab
    summary_ws = MagicMock()
    summary_ws.title = "Summary"
    summary_ws.get_all_values.return_value = [
        ["Month", "Total Amount", "Total Net", "Stripe Fee"],
        ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"],
        ["2024-05", "=SUM('2024-05'!F2:F)", "=SUM('2024-05'!H2:H)", "=SUM('2024-05'!G2:G)"],
    ]
    summary_ws.col_values.return_value = ["Month", "Total", "2024-05"]

    tab1 = MagicMock()
    tab1.title = "2024-07"
    tab2 = MagicMock()
    tab2.title = "2024-05"
    tab3 = MagicMock()
    tab3.title = "OtherSheet"

    mock_spreadsheet.worksheets.return_value = [summary_ws, tab1, tab2, tab3]
    mock_spreadsheet.worksheet.return_value = summary_ws

    sheets_client.sync_summary_sheet(mock_spreadsheet)

    # 2024-07 should be added, 2024-05 already exists, OtherSheet ignored
    summary_ws.append_row.assert_called_once_with(
        ["2024-07", "=SUM('2024-07'!F2:F)", "=SUM('2024-07'!H2:H)", "=SUM('2024-07'!G2:G)"],
        value_input_option="USER_ENTERED",
    )


