from typing import Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.user_bots import UserBotsRepo

async def resolve_bot_key(session: AsyncSession, bot: Bot) -> Optional[int]:
    """
    Возвращает user_bots.id для данного Telegram Bot.
    Если это главный бот (нет записи в user_bots), вернётся None.
    """
    me = await bot.get_me()
    repo = UserBotsRepo(session)
    row = await repo.get_by_tg_bot_id(me.id)
    return row.id if row else None