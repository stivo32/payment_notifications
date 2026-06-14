# This file has been created with the assistance of an AI tool.
import logging
import time
import config
import stripe_client
import supabase_client
import telegram_client
import message_formatter
from state import State

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
            logger.info("Processed event %s", event.id)

    except Exception:
        logger.error("Unhandled exception in poll cycle", exc_info=True)


def main() -> None:
    logger.info("Starting Stripe notifier. Poll interval: %ds", config.POLL_INTERVAL)
    state = State(config.STATE_DB_PATH)

    while True:
        run_poll_cycle(state)
        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
