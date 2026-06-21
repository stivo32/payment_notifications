# This file has been created with the assistance of an AI tool.
import logging
import stripe
import config

stripe.api_key = config.STRIPE_API_KEY

logger = logging.getLogger(__name__)

_price_name_cache: dict[str, str] = {}


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
        _price_name_cache[price_id] = price_id
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
