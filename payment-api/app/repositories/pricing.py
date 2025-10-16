from typing import Optional
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import PricingRule
import os

class PricingRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_manual(self, item_type: str, currency: str, bot_id: int) -> Optional[PricingRule]:
        q = select(PricingRule).where(
            PricingRule.item_type == item_type,
            PricingRule.mode == "manual", # выставляется вручную
            PricingRule.currency == currency,
            PricingRule.is_active == True,  # noqa: E712
            PricingRule.bot_id == bot_id
        ).order_by(PricingRule.id.desc())
        res = await self.session.execute(q)
        return res.scalars().first()

    async def get_active_dynamic(self, item_type: str, currency: str, bot_id: int) -> Optional[PricingRule]:
        q = select(PricingRule).where(
            PricingRule.item_type == item_type,
            PricingRule.mode == "dynamic", # выставляется автоматически
            PricingRule.currency == currency,
            PricingRule.is_active == True,  # noqa: E712,
            PricingRule.bot_id == bot_id
        ).order_by(PricingRule.id.desc())
        res = await self.session.execute(q)
        return res.scalars().first()
    
    async def set_active(self, item_type: str, currency: str, price: float, bot_id: int, markup: float | None = None):
        if await self.get_active_dynamic(item_type=item_type, currency=currency, bot_id=bot_id):
            if markup:
                q = update(PricingRule).where(PricingRule.item_type == item_type, PricingRule.currency == currency, PricingRule.bot_id==bot_id).values(manual_price=price, markup_percent=markup)
            else:
                q = update(PricingRule).where(PricingRule.item_type == item_type, PricingRule.currency == currency, PricingRule.bot_id==bot_id).values(manual_price=price)
        else:
            if not markup:
                markup = float(os.getenv("REFERRAL_PERCENT", "5.0"))
            q = insert(PricingRule).values(
                item_type=item_type,
                mode="dynamic",
                markup_percent=markup,
                currency=currency,
                is_active=True,
                manual_price=price, 
                bot_id=bot_id
            )
        await self.session.execute(q)
        await self.session.commit()
