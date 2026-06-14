# This file has been created with the assistance of an AI tool.
import logging
import time
import requests
import config

logger = logging.getLogger(__name__)

_API_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
_MAX_RETRIES = 3


def send_message(text: str) -> None:
    """Send text message to configured Telegram chat. Retries up to 3 times."""
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": text}
    delay = 1

    for attempt in range(_MAX_RETRIES):
        response = requests.post(_API_URL, json=payload)
        if response.ok:
            return
        logger.warning("Telegram send failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, response.text)
        time.sleep(delay)
        delay *= 2

    logger.error("Telegram send failed after %d retries. Message lost: %s", _MAX_RETRIES, text[:100])
