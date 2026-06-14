# This file has been created with the assistance of an AI tool.
import logging
from supabase import create_client
import config

logger = logging.getLogger(__name__)

_client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def get_user(user_id: str) -> dict | None:
    """Fetch user record by id. Returns dict or None if not found."""
    try:
        response = (
            _client.table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Supabase error fetching user %s: %s", user_id, e)
        return None
