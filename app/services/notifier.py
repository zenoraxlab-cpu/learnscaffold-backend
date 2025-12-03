import httpx
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

async def notify_admin(message: str):
    """
    Sends notification to Telegram admin chat.
    """
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        return  # notifications disabled

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, data={
                "chat_id": ADMIN_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            })
        except Exception:
            pass
