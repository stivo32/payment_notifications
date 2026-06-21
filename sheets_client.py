import logging
from datetime import datetime, timezone

import gspread

import config

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HEADER = ["#", "Purchased", "Email", "Product", "Country", "Amount", "Stripe Fee", "Net", "Session ID", "Payment Intent ID"]

_gc = None


def _get_gc():
    global _gc
    if _gc is None:
        _gc = gspread.service_account(filename=config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES)
    return _gc


def _get_or_create_sheet(spreadsheet, tab_name: str):
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=10)
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
