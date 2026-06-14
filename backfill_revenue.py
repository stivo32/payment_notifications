"""
Recalculate total_revenue in SQLite from all historical Stripe events.
Usage: python backfill_revenue.py [--since 2024-06-08] [--dry-run]
"""
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import stripe
import os
from state import State
import config

stripe.api_key = os.environ["STRIPE_API_KEY"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2024-06-08", help="Start date YYYY-MM-DD (default: 2024-06-08)")
    parser.add_argument("--dry-run", action="store_true", help="Print total without writing to DB")
    args = parser.parse_args()

    since_ts = int(datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    print(f"Fetching all checkout.session.completed events since {args.since}...")

    result = stripe.Event.list(
        type="checkout.session.completed",
        created={"gte": since_ts},
    )
    events = list(result.auto_paging_iter())
    print(f"Found {len(events)} event(s)")

    total = 0.0
    for event in events:
        session = event.data.object
        amount = session.amount_total / 100
        currency = session.currency.upper()
        print(f"  {event.id}  {amount:.2f} {currency}")
        total += amount

    print(f"\nTotal: {total:.2f}")

    if args.dry_run:
        print("Dry run — DB not updated.")
        return

    state = State(config.STATE_DB_PATH)
    with state._conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES ('total_revenue', ?)",
            (str(total),)
        )
    print(f"Updated total_revenue in {config.STATE_DB_PATH}")


if __name__ == "__main__":
    main()
