import requests
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")  # свой chat_id

def notify_admin(message: str):
    """
    Sends a Telegram notification to admin.
    """
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        return  # silently fail, no logging here

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass
