import httpx
import os
from app.utils.logger import logger

# ---------------------------------------------
# Telegram Bot credentials
# ---------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8286772304:AAGB1z3fm-nHIbkE3aNPO40_UOiq2GJf5VE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "406657401")


# ---------------------------------------------
# Send Telegram alert (sync)
# ---------------------------------------------
def send_telegram_alert(message: str):
    """
    Sends message to Telegram using httpx (requests NOT required).
    Safe for Render.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=payload)

        if response.status_code != 200:
            logger.error(f"[TELEGRAM] Error {response.status_code}: {response.text}")
        else:
            logger.info("[TELEGRAM] Alert sent successfully")

    except Exception as e:
        logger.error(f"[TELEGRAM] Exception: {e}")
