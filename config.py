# This file has been created with the assistance of an AI tool.
import os
from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value

STRIPE_API_KEY: str = _require("STRIPE_API_KEY")
SUPABASE_URL: str = _require("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = _require("SUPABASE_SERVICE_KEY")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str = _require("TELEGRAM_CHAT_ID")
POLL_INTERVAL: int = int(os.getenv("STRIPE_POLL_INTERVAL_SECONDS", "60"))
STATE_DB_PATH: str = os.getenv("STATE_DB_PATH", "./state.db")
