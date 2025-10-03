import os
from aiogram import Bot

def get_env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)

async def is_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "creator", "administrator")
    except Exception:
        return False

async def on_startup_banner(bot: Bot):
    me = await bot.get_me()
    print(f"User bot @{me.username} запущен.")
