# This file has been created with the assistance of an AI tool.
import logging
import stripe
import config

stripe.api_key = config.STRIPE_API_KEY

logger = logging.getLogger(__name__)


def fetch_new_events(since_timestamp: int) -> list:
    """Return list of checkout.session.completed events created >= since_timestamp."""
    try:
        result = stripe.Event.list(
            type="checkout.session.completed",
            created={"gte": since_timestamp},
        )
        return list(result.auto_paging_iter())
    except stripe.StripeError as e:
        logger.error("Stripe API error: %s", e)
        return []
