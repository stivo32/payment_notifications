"""
Debug script: fetch recent Stripe events + Supabase user data, dump to JSON file.
Usage: python debug_fetch.py [--hours 24] [--out debug_output.json]
"""
import argparse
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

import stripe
from supabase import create_client

stripe.api_key = os.environ["STRIPE_API_KEY"]
_supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def fetch_events(since_ts: int) -> list:
    result = stripe.Event.list(
        type="checkout.session.completed",
        created={"gte": since_ts},
    )
    return list(result.auto_paging_iter())


def get_user(user_id: str) -> "dict | None":
    try:
        response = _supabase.auth.admin.get_user_by_id(user_id)
        user = response.user
        if not user:
            return None
        return {"id": user.id, "email": user.email, "created_at": str(user.created_at)}
    except Exception as e:
        print(f"  !! Supabase error: {e}")
        return None


def stripe_to_dict(obj) -> object:
    """Convert Stripe object tree to plain Python dicts/lists."""
    raw = json.loads(str(obj))  # Stripe objects have __str__ → JSON
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24, help="Look back N hours (default: 24)")
    parser.add_argument("--out", default="debug_output.json", help="Output file (default: debug_output.json)")
    args = parser.parse_args()

    since_ts = int(time.time()) - args.hours * 3600
    print(f"Fetching checkout.session.completed events since {args.hours}h ago (ts={since_ts})")

    events = fetch_events(since_ts)
    print(f"Found {len(events)} event(s)")

    import message_formatter

    output = []
    for event in events:
        session = event.data.object
        session_dict = stripe_to_dict(session)

        metadata = session_dict.get("metadata") or {}
        user_id = metadata.get("user_id")

        user = None
        user_found = False
        if user_id:
            user = get_user(user_id)
            user_found = user is not None

        record = {
            "event_id": event.id,
            "event_created": event.created,
            "session": session_dict,
            "metadata": metadata,
            "supabase_user_id_looked_up": user_id,
            "supabase_user_found": user_found,
            "supabase_user": user,
            "formatted_message": message_formatter.format_message(session, user),
        }
        output.append(record)
        print(f"  processed event {event.id}")

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nDumped {len(output)} event(s) to {args.out}")


if __name__ == "__main__":
    main()
