from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import User, UserBot
import os

async def resolve_owner_and_bot_key(s: AsyncSession, tg_user_id: int) -> Tuple[Optional[int], Optional[int]]:
    user = (await s.execute(select(User).where(User.tg_user_id == tg_user_id))).scalar_one_or_none()
    if not user:
        return None, None
    ub = (await s.execute(select(UserBot).where(UserBot.owner_user_id == user.id, UserBot.is_active.is_(True)))).scalar_one_or_none()
    return (user.id, ub.id if ub else None)

async def get_main_bot_id(s: AsyncSession):
    tg_bot_id = os.getenv("MAIN_BOT", "")
    q = (
        select(UserBot.id).where(UserBot.tg_bot_id == tg_bot_id)
    )
    return (await s.execute(q)).scalar_one()
