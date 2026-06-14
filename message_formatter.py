from datetime import datetime, timezone


def _fmt_dt(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


_CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}


def _symbol(currency: str) -> str:
    return _CURRENCY_SYMBOLS.get(currency, currency + " ")


def _metadata_dict(metadata) -> dict:
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return dict(metadata)


def format_message(session, user: dict | None, event_created: int | None = None, total_revenue: float | None = None) -> str:
    metadata = _metadata_dict(session.metadata)
    email = session.customer_email or "unknown"
    amount = session.amount_total / 100
    currency = session.currency.upper()
    utm_source = metadata.get("attr_utm_source") or "—"
    purchased_ts = event_created or session.created

    lines = [
        "💳 New Purchase",
        f"Email: {email}",
        f"Amount: {_symbol(currency)}{amount:.2f}",
        f"Source: {utm_source}",
        f"Purchased: {_fmt_dt(purchased_ts)}",
    ]

    if user:
        registered = str(user.get("created_at", ""))[:10]
        if registered:
            lines.append(f"Registered: {registered}")
    else:
        lines.append("⚠️ User not found in DB")

    if total_revenue is not None:
        lines.append(f"Total revenue: {_symbol(currency)}{total_revenue:.2f}")

    return "\n".join(lines)
