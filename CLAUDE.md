# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Long-running Python service that polls Stripe for `checkout.session.completed` events and sends Telegram notifications enriched with Supabase user data. Designed to run as a systemd service on Raspberry Pi.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in .env
```

## Commands

```bash
# Run service
python main.py

# Run all tests
pytest -v

# Run single test file
pytest tests/test_main.py -v

# Run single test
pytest tests/test_main.py::test_poll_cycle_processes_new_event -v
```

## Architecture

The poll loop (`main.py:run_poll_cycle`) ties together four stateless modules:

- **`stripe_client`** — fetches `checkout.session.completed` events since a given Unix timestamp using `stripe.Event.list` with auto-pagination
- **`supabase_client`** — looks up `users` table by `user_id` from `session.metadata`; returns `None` on miss or error
- **`message_formatter`** — pure function, builds Telegram message text from session + optional user dict
- **`telegram_client`** — POSTs to Telegram Bot API with exponential-backoff retry (3 attempts); logs and drops message after all retries fail

**`State`** (`state.py`) is a SQLite wrapper with two tables:
- `processed_events` — deduplication by Stripe event ID (prevents reprocessing on restart)
- `state` — KV store, currently only `last_event_created` (Unix timestamp used as lower bound for next Stripe poll)

On first run, `last_event_created` defaults to `now - 24h`.

**`config.py`** loads all env vars at import time; missing required vars raise `RuntimeError` immediately at startup.

## Key behaviours to preserve

- `run_poll_cycle` catches all exceptions and logs them — the outer `while True` loop must never crash
- `state.mark_processed` uses `INSERT OR IGNORE`, so duplicate events are safe even under concurrent scenarios
- Stripe events are filtered server-side by `created >= since_timestamp`; the event ID check in `is_processed` is a second safety net
- `user_id` comes from `session.metadata`, not from the Stripe customer object — if `metadata.user_id` is absent, Supabase is not queried and the message is still sent
