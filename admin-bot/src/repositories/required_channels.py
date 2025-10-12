from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from typing import List
from src.models import RequiredChannel

class RequiredChannelsRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def list_active(self, bot_key: int) -> List[RequiredChannel]:
        q = await self.s.execute(
            select(RequiredChannel).where(
                RequiredChannel.bot_key == bot_key,
                RequiredChannel.is_active.is_(True)
            ).order_by(RequiredChannel.created_at)
        )
        return list(q.scalars().all())

    async def add(self, bot_key: int, username: str):
        await self.s.execute(
            insert(RequiredChannel).values(
                bot_key=bot_key, channel_username=username, is_active=True
            )
        )
        await self.s.commit()

    async def disable(self, bot_key: int, username: str):
        await self.s.execute(
            update(RequiredChannel)
            .where(RequiredChannel.bot_key == bot_key, RequiredChannel.channel_username == username)
            .values(is_active=False)
        )
        await self.s.commit()
