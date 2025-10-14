from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from typing import Optional
from src.models import PricingRule

class PricingRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def get_active_manual(self, item_type: str, currency: str, bot_id: int) -> Optional[PricingRule]:
        q = await self.s.execute(
            select(PricingRule)
            .where(
                PricingRule.item_type == item_type,
                PricingRule.currency == currency,
                PricingRule.is_active.is_(True),
                PricingRule.mode == "manual",
                PricingRule.bot_id == bot_id
            )
            .order_by(PricingRule.created_at.desc())
        )
        return q.scalars().first()

    async def upsert_manual(self, item_type: str, currency: str, price: float, bot_id: int):
        await self.s.execute(
            insert(PricingRule).values(
                item_type=item_type, currency=currency, mode="manual",
                manual_price=price, is_active=True, bot_id=bot_id
            )
        )
        await self.s.commit()

    async def change_manual(self, item_type: str, currency: str, price: float, bot_id: int):
        await self.s.execute(
            update(PricingRule).where(PricingRule.bot_id == bot_id, PricingRule.currency == currency, PricingRule.item_type == item_type).values(manual_price=price)
        )
        await self.s.commit()
