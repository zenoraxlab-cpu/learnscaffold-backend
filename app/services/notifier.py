import requests
from app.utils.logger import logger
import os

# ---------------------------------------------
# Telegram Bot Credentials
# ---------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8286772304:AAGB1z3fm-nHIbkE3aNPO40_UOiq2GJf5VE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "406657401")


# ---------------------------------------------
# Send message to Telegram
# ---------------------------------------------
def send_telegram_alert(message: str):
    """
    Sends error/alert messages to your Telegram.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=payload, timeout=5)

        if response.status_code != 200:
            logger.error(f"[TELEGRAM] Failed with code {response.status_code}: {response.text}")
        else:
            logger.info("[TELEGRAM] Alert sent successfully")

    except Exception as e:
        logger.error(f"[TELEGRAM] Exception: {e}")
