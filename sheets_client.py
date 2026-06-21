import logging
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HEADER = ["#", "Email", "Amount", "Product", "Country", "Net", "Session ID", "Payment Intent ID"]

_gc = None


def _get_gc():
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES)
        _gc = gspread.authorize(creds)
    return _gc


def _get_or_create_sheet(spreadsheet, tab_name: str):
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=8)
        ws.append_row(_HEADER)
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
        net = round(amount - stripe_fee, 2) if stripe_fee is not None else ""

        ws.append_row([
            row_number,
            session.customer_email or "",
            amount,
            product_name or "",
            country or "",
            net,
            session.id,
            session.payment_intent or "",
        ])
    except Exception:
        logger.error("Failed to append row to Google Sheets", exc_info=True)
