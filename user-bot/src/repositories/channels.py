from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import RequiredChannel

class ChannelsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self) -> List[str]:
        q = select(RequiredChannel.channel_username).where(RequiredChannel.is_active == True)  # noqa: E712
        res = await self.session.execute(q)
        return [row[0] for row in res.all()]
