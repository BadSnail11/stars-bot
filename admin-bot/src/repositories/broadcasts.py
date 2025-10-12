from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update, select, func
from src.models import Broadcast, User

class BroadcastsRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def create(self, author_user_id: int, bot_key: int, text: str):
        res = await self.s.execute(
            insert(Broadcast).values(
                author_user_id=author_user_id,
                text=text, status="draft", bot_key=bot_key
            ).returning(Broadcast.id)
        )
        bid = res.scalar_one()
        await self.s.commit()
        return bid

    async def mark_sent(self, bid: int, partial: bool):
        await self.s.execute(
            update(Broadcast).where(Broadcast.id == bid).values(
                status="partial" if partial else "sent",
                sent_at=func.now()
            )
        )
        await self.s.commit()

    async def audience_tg_ids(self, bot_key: int):
        res = await self.s.execute(select(User.tg_user_id).where(User.bot_key == bot_key))
        return [r for r, in res.all()]
