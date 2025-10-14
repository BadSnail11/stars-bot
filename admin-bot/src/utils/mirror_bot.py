from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import UserBot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def get_mirror_bot(s: AsyncSession, bot_key: int) -> Bot | None:
    ub = (await s.execute(select(UserBot).where(UserBot.id == bot_key, UserBot.is_active.is_(True)))).scalar_one_or_none()
    if not ub:
        return None
    return Bot(token=ub.tg_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
