from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..models import Referral

class ReferralsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_referrer_id_by_referee(self, referee_user_id: int) -> Optional[int]:
        q = select(Referral.referrer_id).where(Referral.referee_id == referee_user_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def create_link_if_absent(self, referrer_id: int, referee_id: int):
        # игнорируем попытку самореферала
        if referrer_id == referee_id:
            return
        # если уже есть — ничего не делаем
        existing = await self.get_referrer_id_by_referee(referee_id)
        if existing is not None:
            return
        await self.session.execute(
            insert(Referral).values(referrer_id=referrer_id, referee_id=referee_id)
        )
        await self.session.commit()
