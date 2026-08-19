"""
Backfill historical Stripe events into Google Sheets.
Usage: python backfill_sheets.py [--since 2024-06-08] [--dry-run] [--sync-summary]
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
    parser.add_argument("--sync-summary", action="store_true", help="Sync Summary tab with all existing month tabs and exit")
    args = parser.parse_args()

    if args.sync_summary:
        print("Syncing Summary sheet with all existing month tabs...")
        sheets_client.sync_summary_sheet()
        print("Summary sync complete.")
        return

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

    if not args.dry_run and written > 0:
        sheets_client.sync_summary_sheet()

    action = "Would write" if args.dry_run else "Written"
    print(f"\nDone. {action}: {written}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
