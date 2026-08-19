import logging
import re
from datetime import datetime, timezone

import gspread

import config

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HEADER = ["#", "Purchased", "Email", "Product", "Country", "Amount", "Stripe Fee", "Net", "Session ID", "Payment Intent ID"]
_SUMMARY_TAB_NAME = "Summary"
_SUMMARY_HEADER = ["Month", "Total Amount", "Total Net", "Stripe Fee"]
_SUMMARY_TOTAL_ROW = ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"]

_gc = None


def _get_gc():
    global _gc
    if _gc is None:
        _gc = gspread.service_account(filename=config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES)
    return _gc


def _get_or_create_summary_sheet(spreadsheet):
    try:
        ws = spreadsheet.worksheet(_SUMMARY_TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        try:
            ws = spreadsheet.get_worksheet(0)
            if ws is not None:
                ws.update_title(_SUMMARY_TAB_NAME)
            else:
                ws = spreadsheet.add_worksheet(title=_SUMMARY_TAB_NAME, rows=1000, cols=10, index=0)
        except Exception:
            ws = spreadsheet.add_worksheet(title=_SUMMARY_TAB_NAME, rows=1000, cols=10, index=0)

    values = ws.get_all_values()
    has_header = len(values) >= 1 and values[0] == _SUMMARY_HEADER
    has_total = len(values) >= 2 and len(values[1]) >= 1 and values[1][0] == "Total"
    if not (has_header and has_total):
        ws.clear()
        ws.append_rows([_SUMMARY_HEADER, _SUMMARY_TOTAL_ROW], value_input_option="USER_ENTERED")
    return ws


def _ensure_month_in_summary(spreadsheet, tab_name: str):
    ws = _get_or_create_summary_sheet(spreadsheet)
    existing_months = ws.col_values(1)
    if tab_name not in existing_months:
        formula_row = [
            tab_name,
            f"=SUM('{tab_name}'!F2:F)",
            f"=SUM('{tab_name}'!H2:H)",
            f"=SUM('{tab_name}'!G2:G)",
        ]
        ws.append_row(formula_row, value_input_option="USER_ENTERED")


def _get_or_create_sheet(spreadsheet, tab_name: str):
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=10)
        ws.append_row(_HEADER)
        _ensure_month_in_summary(spreadsheet, tab_name)
        return ws


def append_row(
    session,
    product_name: str | None,
    country: str | None,
    stripe_fee: float | None,
    event_created: int,
) -> None:
    try:
        tab_name = datetime.fromtimestamp(event_created, tz=timezone.utc).strftime("%Y-%m")
        spreadsheet = _get_gc().open_by_key(config.GOOGLE_SPREADSHEET_ID)
        ws = _get_or_create_sheet(spreadsheet, tab_name)
        row_number = len(ws.get_all_values())

        amount = session.amount_total / 100
        fee = round(stripe_fee, 2) if stripe_fee is not None else ""
        net = round(amount - stripe_fee, 2) if stripe_fee is not None else ""

        purchased = datetime.fromtimestamp(event_created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        ws.append_row([
            row_number,
            purchased,
            session.customer_email or "",
            product_name or "",
            country or "",
            amount,
            fee,
            net,
            session.id,
            session.payment_intent or "",
        ])
    except Exception:
        logger.error("Failed to append row to Google Sheets", exc_info=True)


def sync_summary_sheet(spreadsheet=None) -> None:
    try:
        if spreadsheet is None:
            spreadsheet = _get_gc().open_by_key(config.GOOGLE_SPREADSHEET_ID)

        summary_ws = _get_or_create_summary_sheet(spreadsheet)

        month_tabs = [
            ws.title for ws in spreadsheet.worksheets()
            if re.match(r"^\d{4}-\d{2}$", ws.title)
        ]
        month_tabs.sort()

        all_rows = [_SUMMARY_HEADER, _SUMMARY_TOTAL_ROW]
        for month in month_tabs:
            all_rows.append([
                month,
                f"=SUM('{month}'!F2:F)",
                f"=SUM('{month}'!H2:H)",
                f"=SUM('{month}'!G2:G)",
            ])

        summary_ws.clear()
        summary_ws.append_rows(all_rows, value_input_option="USER_ENTERED")
    except Exception:
        logger.error("Failed to sync summary sheet", exc_info=True)


