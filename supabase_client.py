# This file has been created with the assistance of an AI tool.
import logging
from supabase import create_client
import config

logger = logging.getLogger(__name__)

_client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def get_user(user_id: str) -> dict | None:
    """Fetch user from auth.users by id. Returns dict or None if not found."""
    try:
        response = _client.auth.admin.get_user_by_id(user_id)
        user = response.user
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "created_at": str(user.created_at),
        }
    except Exception as e:
        logger.error("Supabase error fetching user %s: %s", user_id, e)
        return None


def get_purchase_country(session_id: str) -> str | None:
    try:
        response = (
            _client.table("purchase_logs")
            .select("buyer_country")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0].get("buyer_country")
        return None
    except Exception as e:
        logger.error("Supabase error fetching country for session %s: %s", session_id, e)
        return None
