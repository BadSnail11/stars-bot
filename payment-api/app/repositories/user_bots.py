from typing import Optional
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserBot  # предполагается, что у тебя есть модель User
from sqlalchemy.orm import registry
from sqlalchemy import Column, BigInteger, Boolean, Text, TIMESTAMP

mapper_registry = registry()
Base = mapper_registry.generate_base()



class UserBotsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_owner(self, owner_user_id: int) -> Optional[UserBot]:
        res = await self.session.execute(
            select(UserBot).where(UserBot.owner_user_id == owner_user_id)
        )
        return res.scalar_one_or_none()
    
    async def get_by_tg_bot_id(self, tg_bot_id: int) -> Optional[UserBot]:
        res = await self.session.execute(
            select(UserBot).where(UserBot.tg_bot_id == tg_bot_id)
        )
        return res.scalar_one_or_none()


    async def create(self, owner_user_id: int, token: str, username: str, tg_bot_id: int) -> UserBot:
        res = await self.session.execute(
            insert(UserBot).values(
                owner_user_id=owner_user_id,
                tg_bot_token=token,
                bot_username=username,
                tg_bot_id=tg_bot_id,
                is_active=True,
            ).returning(UserBot)
        )
        bot = res.scalar_one()
        await self.session.commit()
        return bot
    
    async def set_tg_bot_id(self, owner_user_id: int, tg_bot_id: int):
        await self.session.execute(
            update(UserBot)
            .where(UserBot.owner_user_id == owner_user_id)
            .values(tg_bot_id=tg_bot_id)
        )
        await self.session.commit()

    async def deactivate(self, owner_user_id: int):
        await self.session.execute(
            update(UserBot)
            .where(UserBot.owner_user_id == owner_user_id)
            .values(is_active=False)
        )
        await self.session.commit()

    async def get_all(self):
        r = await self.session.execute(select(UserBot))
        bots = r.scalars().all()
        return bots
