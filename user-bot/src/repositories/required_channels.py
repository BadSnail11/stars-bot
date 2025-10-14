from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import RequiredChannel  # модель required_channels

class RequiredChannelsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_for_bot_key(self, bot_key: Optional[int]) -> List[RequiredChannel]:
        # print(bot_key)
        if bot_key is None:
            q = select(RequiredChannel).where(
                RequiredChannel.bot_key.is_(None),
                RequiredChannel.is_active.is_(True),
            ).order_by(RequiredChannel.created_at)
        else:
            q = select(RequiredChannel).where(
                RequiredChannel.bot_key == bot_key,
                RequiredChannel.is_active.is_(True),
            ).order_by(RequiredChannel.created_at)

        res = await self.session.execute(q)
        return list(res.scalars().all())
