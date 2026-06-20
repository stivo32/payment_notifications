# Google Sheets Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append a row to a Google Sheets spreadsheet on each Stripe checkout event, grouped by month tab, and provide a backfill script for historical events.

**Architecture:** New stateless `sheets_client.py` module mirrors `telegram_client.py`. `run_poll_cycle` in `main.py` fetches product name, Stripe fee, and country after sending the Telegram message, then calls `sheets_client.append_row`. A `backfill_sheets.py` CLI script iterates historical events and uses the same client.

**Tech Stack:** `gspread>=6.0.0`, `google-auth>=2.0.0`, Google Sheets API (Service Account auth), existing `stripe`, `supabase` libs.

## Global Constraints

- Python 3.11+; use `str | None` union syntax (not `Optional`)
- All errors in new Sheets/Stripe/Supabase calls must be caught and logged — never raise into the poll cycle
- Follow existing test pattern: `unittest.mock.patch` on module-level clients, `MagicMock` for objects
- Run tests with: `source venv/bin/activate && pytest -v`

---

### Task 1: state.py — sheets_exported_events table

**Files:**
- Modify: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces: `State.is_sheets_exported(event_id: str) -> bool`, `State.mark_sheets_exported(event_id: str) -> None`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_state.py`:

```python
def test_is_sheets_exported_returns_false_for_new_event(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    assert s.is_sheets_exported("evt_123") is False


def test_mark_sheets_exported_then_is_sheets_exported_returns_true(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    s.mark_sheets_exported("evt_123")
    assert s.is_sheets_exported("evt_123") is True


def test_mark_sheets_exported_is_idempotent(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    s.mark_sheets_exported("evt_123")
    s.mark_sheets_exported("evt_123")  # should not raise
    assert s.is_sheets_exported("evt_123") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && pytest tests/test_state.py::test_is_sheets_exported_returns_false_for_new_event tests/test_state.py::test_mark_sheets_exported_then_is_sheets_exported_returns_true tests/test_state.py::test_mark_sheets_exported_is_idempotent -v
```

Expected: FAIL with `AttributeError: 'State' object has no attribute 'is_sheets_exported'`

- [ ] **Step 3: Add table creation to `state.py`**

In `State._init_db`, after the existing `conn.execute` for `state` table, add:

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS sheets_exported_events (
        event_id TEXT PRIMARY KEY,
        exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

- [ ] **Step 4: Add methods to `State` class in `state.py`**

Append after `get_total_revenue`:

```python
def is_sheets_exported(self, event_id: str) -> bool:
    with self._conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sheets_exported_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None

def mark_sheets_exported(self, event_id: str) -> None:
    with self._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sheets_exported_events (event_id) VALUES (?)",
            (event_id,)
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: add sheets_exported_events table and methods to State"
```

---

### Task 2: config.py + requirements.txt + .env.example

**Files:**
- Modify: `config.py`, `requirements.txt`, `.env.example`

**Interfaces:**
- Produces: `config.GOOGLE_SERVICE_ACCOUNT_JSON: str`, `config.GOOGLE_SPREADSHEET_ID: str`

- [ ] **Step 1: Add deps to `requirements.txt`**

Append to `requirements.txt`:

```
gspread>=6.0.0
google-auth>=2.0.0
```

- [ ] **Step 2: Install new deps**

```bash
source venv/bin/activate && pip install gspread>=6.0.0 "google-auth>=2.0.0"
```

Expected: Successfully installed gspread and google-auth (or already satisfied)

- [ ] **Step 3: Add env vars to `config.py`**

After the `STATE_DB_PATH` line, append:

```python
GOOGLE_SERVICE_ACCOUNT_JSON: str = _require("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SPREADSHEET_ID: str = _require("GOOGLE_SPREADSHEET_ID")
```

- [ ] **Step 4: Add env vars to `.env.example`**

Append to `.env.example`:

```
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account-key.json
GOOGLE_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

- [ ] **Step 5: Commit**

```bash
git add config.py requirements.txt .env.example
git commit -m "feat: add Google Sheets config vars and dependencies"
```

---

### Task 3: stripe_client.py — fetch_product_name + fetch_stripe_fee

**Files:**
- Modify: `stripe_client.py`
- Test: `tests/test_stripe_client.py`

**Interfaces:**
- Produces:
  - `fetch_product_name(price_id: str) -> str` — returns product name or `price_id` on error
  - `fetch_stripe_fee(payment_intent_id: str) -> float | None` — returns fee in major currency units or `None` on error

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stripe_client.py`:

```python
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
    mock_pi.latest_charge.balance_transaction = None
    type(mock_pi.latest_charge.balance_transaction).fee = property(lambda self: (_ for _ in ()).throw(AttributeError))

    with patch("stripe_client.stripe.PaymentIntent.retrieve", return_value=mock_pi):
        # AttributeError on .fee access — should return None
        result = stripe_client.fetch_stripe_fee("pi_nobt")

    assert result is None
```

Add `import pytest` at the top of `tests/test_stripe_client.py` (after existing imports).

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stripe_client.py::test_fetch_product_name_returns_name tests/test_stripe_client.py::test_fetch_stripe_fee_returns_fee_in_major_units -v
```

Expected: FAIL with `AttributeError: module 'stripe_client' has no attribute 'fetch_product_name'`

- [ ] **Step 3: Add module-level cache and new functions to `stripe_client.py`**

After the `logger = ...` line, add the cache dict. Then append the two functions after `fetch_new_events`:

```python
_price_name_cache: dict[str, str] = {}


def fetch_product_name(price_id: str) -> str:
    if price_id in _price_name_cache:
        return _price_name_cache[price_id]
    try:
        price = stripe.Price.retrieve(price_id, expand=["product"])
        name = price.product.name
        _price_name_cache[price_id] = name
        return name
    except stripe.StripeError as e:
        logger.error("Failed to fetch product name for %s: %s", price_id, e)
        return price_id


def fetch_stripe_fee(payment_intent_id: str) -> float | None:
    try:
        pi = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            expand=["latest_charge.balance_transaction"],
        )
        fee = pi.latest_charge.balance_transaction.fee
        return fee / 100
    except (stripe.StripeError, AttributeError, TypeError) as e:
        logger.error("Failed to fetch Stripe fee for %s: %s", payment_intent_id, e)
        return None
```

- [ ] **Step 4: Run all stripe_client tests**

```bash
pytest tests/test_stripe_client.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add stripe_client.py tests/test_stripe_client.py
git commit -m "feat: add fetch_product_name and fetch_stripe_fee to stripe_client"
```

---

### Task 4: supabase_client.py — get_purchase_country

**Files:**
- Modify: `supabase_client.py`
- Test: `tests/test_supabase_client.py`

**Interfaces:**
- Produces: `get_purchase_country(session_id: str) -> str | None`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_supabase_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_supabase_client.py::test_get_purchase_country_returns_country_when_found -v
```

Expected: FAIL with `AttributeError: module 'supabase_client' has no attribute 'get_purchase_country'`

- [ ] **Step 3: Add function to `supabase_client.py`**

Append after `get_user`:

```python
def get_purchase_country(session_id: str) -> str | None:
    try:
        response = (
            _client.table("purchase_logs")
            .select("buyer_country")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0].get("buyer_country")
        return None
    except Exception as e:
        logger.error("Supabase error fetching country for session %s: %s", session_id, e)
        return None
```

- [ ] **Step 4: Run all supabase_client tests**

```bash
pytest tests/test_supabase_client.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add supabase_client.py tests/test_supabase_client.py
git commit -m "feat: add get_purchase_country to supabase_client"
```

---

### Task 5: sheets_client.py — new module

**Files:**
- Create: `sheets_client.py`
- Create: `tests/test_sheets_client.py`

**Interfaces:**
- Consumes: `config.GOOGLE_SERVICE_ACCOUNT_JSON: str`, `config.GOOGLE_SPREADSHEET_ID: str`
- Produces: `append_row(session, product_name: str | None, country: str | None, stripe_fee: float | None, event_created: int) -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sheets_client.py`:

```python
from unittest.mock import MagicMock, patch, call
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sheets_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sheets_client'`

- [ ] **Step 3: Create `sheets_client.py`**

```python
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
```

- [ ] **Step 4: Run all sheets_client tests**

```bash
pytest tests/test_sheets_client.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sheets_client.py tests/test_sheets_client.py
git commit -m "feat: add sheets_client module with append_row"
```

---

### Task 6: main.py — wire Sheets into run_poll_cycle

**Files:**
- Modify: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes:
  - `stripe_client.fetch_product_name(price_id: str) -> str`
  - `stripe_client.fetch_stripe_fee(payment_intent_id: str) -> float | None`
  - `supabase_client.get_purchase_country(session_id: str) -> str | None`
  - `sheets_client.append_row(session, product_name, country, stripe_fee, event_created) -> None`

- [ ] **Step 1: Write failing test**

Append to `tests/test_main.py`:

```python
def test_poll_cycle_calls_sheets_append_row():
    event = _make_event("evt_1", 1700000100)
    event.data.object.id = "cs_live_abc"
    event.data.object.payment_intent = "pi_abc"
    event.data.object.metadata = {"user_id": "uid_abc", "price_id": "price_xyz"}
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = False

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.stripe_client.fetch_product_name", return_value="Pro Plan") as mock_name, \
         patch("main.stripe_client.fetch_stripe_fee", return_value=0.59) as mock_fee, \
         patch("main.supabase_client.get_user", return_value=None), \
         patch("main.supabase_client.get_purchase_country", return_value="LT") as mock_country, \
         patch("main.telegram_client.send_message"), \
         patch("main.message_formatter.format_message", return_value="msg"), \
         patch("main.sheets_client.append_row") as mock_sheets:
        main.run_poll_cycle(mock_state)

    mock_name.assert_called_once_with("price_xyz")
    mock_fee.assert_called_once_with("pi_abc")
    mock_country.assert_called_once_with("cs_live_abc")
    mock_sheets.assert_called_once_with(
        event.data.object, "Pro Plan", "LT", 0.59, 1700000100
    )


def test_poll_cycle_sheets_not_called_when_event_already_processed():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = True

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.sheets_client.append_row") as mock_sheets:
        main.run_poll_cycle(mock_state)

    mock_sheets.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py::test_poll_cycle_calls_sheets_append_row -v
```

Expected: FAIL — `sheets_client` not imported or `append_row` not called

- [ ] **Step 3: Update `main.py`**

Add import after existing imports:

```python
import sheets_client
```

Replace the body of `run_poll_cycle` with:

```python
def run_poll_cycle(state: State) -> None:
    try:
        since = state.get_last_event_created()
        events = stripe_client.fetch_new_events(since_timestamp=since)

        for event in events:
            if state.is_processed(event.id):
                continue

            session = event.data.object
            meta = session.metadata
            metadata = meta.to_dict() if hasattr(meta, "to_dict") else dict(meta or {})
            user_id = metadata.get("user_id")
            user = supabase_client.get_user(user_id) if user_id else None

            state.mark_processed(event.id)
            state.set_last_event_created(event.created)
            total_revenue = state.add_revenue(session.amount_total / 100)

            text = message_formatter.format_message(session, user, event.created, total_revenue)
            telegram_client.send_message(text)

            price_id = metadata.get("price_id")
            product_name = stripe_client.fetch_product_name(price_id) if price_id else None
            stripe_fee = stripe_client.fetch_stripe_fee(session.payment_intent)
            country = supabase_client.get_purchase_country(session.id)
            sheets_client.append_row(session, product_name, country, stripe_fee, event.created)

            logger.info("Processed event %s", event.id)

    except Exception:
        logger.error("Unhandled exception in poll cycle", exc_info=True)
```

- [ ] **Step 4: Run all main tests**

```bash
pytest tests/test_main.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: wire sheets_client into run_poll_cycle"
```

---

### Task 7: backfill_sheets.py — CLI backfill script

**Files:**
- Create: `backfill_sheets.py`

**Interfaces:**
- Consumes:
  - `state.State.is_sheets_exported(event_id: str) -> bool`
  - `state.State.mark_sheets_exported(event_id: str) -> None`
  - `stripe_client.fetch_product_name(price_id: str) -> str`
  - `stripe_client.fetch_stripe_fee(payment_intent_id: str) -> float | None`
  - `supabase_client.get_purchase_country(session_id: str) -> str | None`
  - `sheets_client.append_row(session, product_name, country, stripe_fee, event_created) -> None`

- [ ] **Step 1: Create `backfill_sheets.py`**

```python
"""
Backfill historical Stripe events into Google Sheets.
Usage: python backfill_sheets.py [--since 2024-06-08] [--dry-run]
"""
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import stripe
import config
import sheets_client
import stripe_client
import supabase_client
from state import State

stripe.api_key = config.STRIPE_API_KEY


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2024-06-08", help="Start date YYYY-MM-DD (default: 2024-06-08)")
    parser.add_argument("--dry-run", action="store_true", help="Print rows without writing to Sheets")
    args = parser.parse_args()

    since_ts = int(datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    print(f"Fetching all checkout.session.completed events since {args.since}...")

    result = stripe.Event.list(
        type="checkout.session.completed",
        created={"gte": since_ts},
    )
    events = list(result.auto_paging_iter())
    print(f"Found {len(events)} event(s)")

    state = State(config.STATE_DB_PATH)
    written = 0
    skipped = 0

    for event in events:
        if state.is_sheets_exported(event.id):
            print(f"  SKIP {event.id} (already exported)")
            skipped += 1
            continue

        session = event.data.object
        meta = session.metadata
        metadata = meta.to_dict() if hasattr(meta, "to_dict") else dict(meta or {})

        price_id = metadata.get("price_id")
        product_name = stripe_client.fetch_product_name(price_id) if price_id else None
        stripe_fee = stripe_client.fetch_stripe_fee(session.payment_intent)
        country = supabase_client.get_purchase_country(session.id)

        ts = datetime.fromtimestamp(event.created, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  {event.id}  {ts}  {session.customer_email}  {session.amount_total/100:.2f}  {product_name}  {country}  fee={stripe_fee}")

        if not args.dry_run:
            sheets_client.append_row(session, product_name, country, stripe_fee, event.created)
            state.mark_sheets_exported(event.id)
        written += 1

    action = "Would write" if args.dry_run else "Written"
    print(f"\nDone. {action}: {written}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run smoke test**

```bash
source venv/bin/activate && python backfill_sheets.py --since 2026-06-01 --dry-run
```

Expected: prints found events with their data, no writes to Sheets, no exceptions

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backfill_sheets.py
git commit -m "feat: add backfill_sheets script for historical Google Sheets export"
```
