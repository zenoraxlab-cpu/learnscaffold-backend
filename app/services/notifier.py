import os
import httpx
from app.utils.logger import logger

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

async def notify_admin(text: str):
    """
    Sends Telegram notification about errors.
    """
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("[NOTIFIER] Bot or chat_id not configured")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(url, data={"chat_id": ADMIN_CHAT_ID, "text": text})
            logger.info("[NOTIFIER] Sent notification")
        except Exception as e:
            logger.error(f"[NOTIFIER] Failed to send message: {e}")
