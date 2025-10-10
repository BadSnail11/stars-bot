from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import PricingRule

class PricingRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_manual(self, item_type: str, currency: str) -> Optional[PricingRule]:
        q = select(PricingRule).where(
            PricingRule.item_type == item_type,
            PricingRule.mode == "manual", # выставляется вручную
            PricingRule.currency == currency,
            PricingRule.is_active == True,  # noqa: E712
        ).order_by(PricingRule.id.desc())
        res = await self.session.execute(q)
        return res.scalars().first()

    async def get_active_dynamic(self, item_type: str, currency: str) -> Optional[PricingRule]:
        q = select(PricingRule).where(
            PricingRule.item_type == item_type,
            PricingRule.mode == "dynamic", # выставляется автоматически
            PricingRule.currency == currency,
            PricingRule.is_active == True,  # noqa: E712
        ).order_by(PricingRule.id.desc())
        res = await self.session.execute(q)
        return res.scalars().first()
