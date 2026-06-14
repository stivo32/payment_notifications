# This file has been created with the assistance of an AI tool.

# Stripe Notification Bot — Design Spec

**Date:** 2026-06-14  
**Status:** Approved  

---

## Overview

Long-running Python process on Raspberry Pi. Polls Stripe for new `checkout.session.completed` events, enriches with Supabase user data where needed, sends formatted message to Telegram bot.

---

## Architecture

### Module Structure

```
stripe_notification/
├── main.py                 # Entry point, polling loop
├── config.py               # Loads env vars via python-dotenv
├── stripe_client.py        # Stripe API: fetch checkout.session.completed events
├── supabase_client.py      # Supabase: get user record by user_id
├── telegram_client.py      # Telegram Bot API: send message
├── state.py                # SQLite: processed event IDs + last_event_created timestamp
├── message_formatter.py    # Combine Stripe + Supabase data into message text
├── .env                    # Secrets (not in git)
└── requirements.txt
```

### Data Flow

```
main.py polling loop (every STRIPE_POLL_INTERVAL_SECONDS)
  → stripe_client: fetch events with type=checkout.session.completed, created[gte]=last_event_created
  → state: filter out already-processed event IDs
  → for each new event:
      → supabase_client: GET user by session.metadata.user_id (if metadata present)
      → message_formatter: build message from Stripe data + Supabase data
      → telegram_client: send to TELEGRAM_CHAT_ID (3 retries, exponential backoff)
      → state: mark event ID as processed, update last_event_created
```

---

## Components

### `config.py`
Loads and validates required env vars at startup. Fails fast if any required var is missing.

Required env vars:
- `STRIPE_API_KEY`
- `STRIPE_POLL_INTERVAL_SECONDS` (default: 60)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `STATE_DB_PATH` (default: `./state.db`)

### `stripe_client.py`
Uses official `stripe` Python SDK. Fetches `checkout.session.completed` events using `stripe.Event.list(type="checkout.session.completed", created={"gte": last_ts})`. Returns list of event objects.

### `state.py`
SQLite via `sqlite3` stdlib. Two tables:

```sql
CREATE TABLE processed_events (
    event_id TEXT PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE state (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- key='last_event_created' stores unix timestamp of last seen event
```

On first run: `last_event_created` defaults to `now - 24h`.

### `supabase_client.py`
Uses `supabase-py` SDK. Fetches user record by `user_id` from `session.metadata`. If metadata missing or user not found, returns `None` — caller handles gracefully.

### `message_formatter.py`
Builds message string. Primary data source: Stripe `checkout.session` object (email, amount, currency, product name from line items if available, metadata fields). Secondary: Supabase user record (registration date, any fields missing from Stripe).

Message format (Markdown):
```
💳 New Purchase
Email: user@example.com
Amount: $49.00 USD
Registered: 2025-01-15
```

If Supabase user not found: appends `⚠️ User not found in DB`.

### `telegram_client.py`
Uses `requests` or `python-telegram-bot` SDK. Sends message via `sendMessage` to `TELEGRAM_CHAT_ID`. Retries 3 times with exponential backoff (1s, 2s, 4s) on failure. If all retries fail: logs `ERROR`, marks event as processed anyway to prevent duplicate sends on recovery.

### `main.py`
Infinite loop:
```python
while True:
    try:
        run_poll_cycle()
    except Exception as e:
        logging.error("Unhandled exception in poll cycle", exc_info=True)
    time.sleep(config.POLL_INTERVAL)
```

---

## Deployment on Raspberry Pi

### systemd service

```ini
[Unit]
Description=Stripe Notification Bot
After=network.target

[Service]
WorkingDirectory=/home/pi/stripe_notification
ExecStart=/home/pi/stripe_notification/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/pi/stripe_notification/.env

[Install]
WantedBy=multi-user.target
```

### Logging
Standard `logging` module → stdout → captured by `journalctl`. Level: `INFO` for normal ops, `ERROR` for failures.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Stripe API unavailable | Log ERROR, skip cycle, continue loop |
| Supabase user not found | Include `⚠️ User not found in DB` in message, continue |
| Telegram send failed (all retries) | Log ERROR, mark event processed, continue |
| Unhandled exception in loop | Log ERROR with traceback, continue loop |

---

## Dependencies

```
stripe
supabase
python-dotenv
requests
```

---

## Out of Scope

- Webhook-based event delivery
- Multiple Telegram chat targets
- Dashboard / UI
- Historical backfill beyond 24h on first run
