# Stripe Payment Notifier

Long-running Python service that polls Stripe for new purchases and sends Telegram notifications enriched with Supabase user data. Designed to run on Raspberry Pi.

## How it works

1. Polls Stripe for `checkout.session.completed` events every N seconds
2. Looks up buyer in Supabase via `session.metadata.user_id`
3. Sends formatted message to Telegram bot
4. Tracks processed event IDs in SQLite to prevent duplicates

## Requirements

- Python 3.11+
- Stripe account with API key
- Supabase project with a `users` table
- Telegram bot token + chat ID

## Setup

```bash
git clone https://github.com/stivo32/payment_notifications.git
cd payment_notifications
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in .env with real credentials
```

## Configuration

| Variable | Description |
|---|---|
| `STRIPE_API_KEY` | Stripe secret key (`sk_live_...`) |
| `STRIPE_POLL_INTERVAL_SECONDS` | Poll interval in seconds (default: 60) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Target chat/channel ID |
| `STATE_DB_PATH` | SQLite DB path (default: `./state.db`) |

## Run

```bash
python main.py
```

## Backfill historical revenue

On a fresh machine the SQLite `state.db` starts with `total_revenue = 0`. Run this once before starting the service to seed the counter from Stripe history:

```bash
python backfill_revenue.py --since 2026-06-08 --dry-run  # verify total
python backfill_revenue.py --since 2026-06-08            # write to DB
```

## Deploy on Raspberry Pi (systemd)

```bash
# Copy project to Pi
scp -r . pi@raspberrypi:/home/pi/payment_notifications

# On the Pi
cd /home/pi/payment_notifications
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env  # fill in credentials

# Install and start service
sudo cp stripe-notifier.service /etc/systemd/system/
sudo systemctl enable stripe-notifier
sudo systemctl start stripe-notifier

# View logs
journalctl -u stripe-notifier -f
```

## Telegram message format

```
💳 New Purchase
Email: user@example.com
Amount: $49.00 USD
Registered: 2025-01-15
```

If user not found in Supabase: `⚠️ User not found in DB` appended.

## Run tests

```bash
pip install -r requirements-dev.txt
pytest -v
```
