# This file has been created with the assistance of an AI tool.


def format_message(session, user: dict | None) -> str:
    """Build Telegram message from Stripe session and optional Supabase user."""
    email = session.customer_email or "unknown"
    amount = session.amount_total / 100
    currency = session.currency.upper()

    lines = [
        "💳 New Purchase",
        f"Email: {email}",
        f"Amount: ${amount:.2f} {currency}",
    ]

    if user:
        registered = user.get("created_at", "")[:10]  # YYYY-MM-DD
        if registered:
            lines.append(f"Registered: {registered}")
    else:
        lines.append("⚠️ User not found in DB")

    return "\n".join(lines)
