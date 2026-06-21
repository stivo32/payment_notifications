# Google Sheets Export — Design Spec

**Date:** 2026-06-20  
**Status:** Approved

## Overview

On each successful Stripe `checkout.session.completed` event, append a row to a Google Sheets spreadsheet. Rows are grouped by month — each month gets its own sheet tab named `YYYY-MM`. A backfill script covers historical events.

## Columns

| Column | Source | Notes |
|---|---|---|
| `#` | `len(existing rows in sheet) + 1` | Recomputed before each append |
| Email | `session.customer_email` | |
| Amount | `session.amount_total / 100` | Float, e.g. `9.99` |
| Product | `stripe.Price.retrieve(price_id, expand=['product']).product.name` | Cached in-memory by `price_id`; falls back to raw `price_id` on error |
| Country | `supabase: public.purchase_logs WHERE session_id = session.id → buyer_country` | Empty string if not found |
| Net | `amount - balance_transaction.fee / 100` | Fee fetched via `payment_intent → charge → balance_transaction`; empty if unavailable |
| Session ID | `session.id` | `cs_live_...` |
| Payment Intent ID | `session.payment_intent` | `pi_...` |

## Architecture

### New files

**`sheets_client.py`** — stateless module, mirrors `telegram_client.py` pattern:
- `append_row(session, product_name, country, stripe_fee_amount) -> None`
- Resolves sheet tab name from event timestamp: `datetime.utcfromtimestamp(ts).strftime("%Y-%m")`
- Creates sheet tab if it does not exist
- Computes row number from current row count in sheet
- Initialises `gspread` client from service account JSON at module load time

**`backfill_sheets.py`** — CLI script, mirrors `backfill_revenue.py` pattern:
- Args: `--since YYYY-MM-DD`, `--dry-run`
- Fetches all `checkout.session.completed` events since date
- Skips events already in `sheets_exported_events` SQLite table
- For each event: fetches price/product from Stripe, fee from balance_transaction, country from Supabase `purchase_logs`
- Appends row via `sheets_client.append_row`
- Marks event in `sheets_exported_events` after successful write

### Modified files

**`main.py` (`run_poll_cycle`)** — fetches product name, fee, and country then calls Sheets:
```python
price_id = metadata.get("price_id")
product_name = stripe_client.fetch_product_name(price_id) if price_id else price_id
stripe_fee = stripe_client.fetch_stripe_fee(session.payment_intent)
country = supabase_client.get_purchase_country(session.id)
sheets_client.append_row(session, product_name, country, stripe_fee)
```

**`stripe_client.py`** — two new functions:
- `fetch_product_name(price_id: str) -> str` — calls `stripe.Price.retrieve(price_id, expand=['product'])`, caches result in module-level dict `_price_name_cache`
- `fetch_stripe_fee(payment_intent_id: str) -> float | None` — calls `stripe.PaymentIntent.retrieve(pi_id, expand=['latest_charge.balance_transaction'])`, returns `fee / 100`

**`supabase_client.py`** — new function:
```python
def get_purchase_country(session_id: str) -> str | None
```
Queries `public.purchase_logs` where `session_id = session_id`, returns `buyer_country` or `None`.

**`state.py`** — new table `sheets_exported_events`:
```sql
CREATE TABLE IF NOT EXISTS sheets_exported_events (
    event_id TEXT PRIMARY KEY,
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```
New methods: `is_sheets_exported(event_id)`, `mark_sheets_exported(event_id)`.

**`config.py`** — two new required env vars:
```
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json
GOOGLE_SPREADSHEET_ID=<id from spreadsheet URL>
```

## External API calls per event

| Call | Purpose | Caching |
|---|---|---|
| `stripe.Price.retrieve(price_id, expand=['product'])` | Product name | In-memory dict, process lifetime |
| `stripe.PaymentIntent.retrieve(pi_id, expand=['latest_charge.balance_transaction'])` | Stripe fee | None |
| Supabase `purchase_logs` query | Country | None |
| Google Sheets append | Write row | None |

## Error handling

Sheets write is non-critical. Errors are logged and swallowed — the poll cycle continues. Telegram notification is always attempted first and is unaffected by Sheets failures.

No retry logic for Sheets writes. Missed rows can be recovered by running `backfill_sheets.py`.

Price fetch errors fall back to raw `price_id` string. Fee and country fetch errors write an empty cell. None of these abort the row append.

## Dependencies

```
gspread>=6.0.0
google-auth>=2.0.0
```

## Setup steps (operator)

1. Google Cloud Console → enable Google Sheets API
2. Create Service Account → download JSON key
3. Share target spreadsheet with service account email as Editor
4. Set `GOOGLE_SERVICE_ACCOUNT_JSON` and `GOOGLE_SPREADSHEET_ID` in `.env`
