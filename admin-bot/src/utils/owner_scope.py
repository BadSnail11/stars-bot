from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import User, UserBot

async def resolve_owner_and_bot_key(s: AsyncSession, tg_user_id: int) -> Tuple[Optional[int], Optional[int]]:
    user = (await s.execute(select(User).where(User.tg_user_id == tg_user_id))).scalar_one_or_none()
    if not user:
        return None, None
    ub = (await s.execute(select(UserBot).where(UserBot.owner_user_id == user.id, UserBot.is_active.is_(True)))).scalar_one_or_none()
    return (user.id, ub.id if ub else None)
