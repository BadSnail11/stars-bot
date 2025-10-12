from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.models import User, UserBot

class UserBotsRepo:
    def __init__(self, session: AsyncSession):
        self.s = session

    async def get_by_owner_tg(self, tg_user_id: int) -> Optional[UserBot]:
        q = await self.s.execute(
            select(UserBot).join(User, User.id == UserBot.owner_user_id)
            .where(User.tg_user_id == tg_user_id, UserBot.is_active.is_(True))
        )
        return q.scalar_one_or_none()
