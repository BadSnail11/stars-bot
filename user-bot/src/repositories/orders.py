from typing import Optional
from sqlalchemy import select, insert, update, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Order


class OrdersRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending_ton_order(
        self, user_id: int, username: str | None, recipient: str | None, type: str, amount: float, price: float, memo: str, wallet: str
    ) -> Order:
        """
        Создаёт заказ в статусе pending для оплаты TON.
        """
        payload = {"wallet": wallet, "memo": memo, "network": "TON", "type": type, "amount": amount, "recipient": recipient}
        res = await self.session.execute(
            insert(Order).values(
                user_id=user_id,
                username=username,
                recipient=None,
                type=type,          # временно: используем stars, позже можно добавить 'ton'
                amount=amount,
                price=price,
                income=None,
                currency="TON",
                status="pending",
                message=None,
                gateway_payload=payload,
                created_at=func.now(),
            ).returning(Order)
        )
        order = res.scalar_one()
        await self.session.commit()
        return order
    
    async def create_pending_sbp_order(
        self, user_id: int, username: str | None, recipient: str | None, type: str, amount: float, price: float, transaction_id: str, redirect_url: str
    ) -> Order:
        payload = {"provider": "platega", "paymentMethod": "SBP", "redirect": redirect_url,
                   "transactionId": transaction_id, "type": type, "amount": amount, "recipient": recipient}
        res = await self.session.execute(
            insert(Order).values(
                user_id=user_id, username=username, recipient=recipient,
                type=type, amount=amount, price=price,
                income=None, currency="RUB", status="pending",
                message=None, gateway_payload=payload, created_at=func.now(),
            ).returning(Order)
        )
        order = res.scalar_one()
        await self.session.commit()
        return order
    
    async def mark_paid(self, order_id: int, tx_hash: str, income: float | None = None):
        # безопасно мёржим {"tx_hash": "<...>"} в gateway_payload
        new_kv = cast({"tx_hash": tx_hash}, JSONB)
        merged_payload = func.coalesce(Order.gateway_payload, cast({}, JSONB)).op("||")(new_kv)

        await self.session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                status="paid",
                paid_at=func.now(),
                income=income,
                gateway_payload=merged_payload,
            )
        )
        await self.session.commit()

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        res = await self.session.execute(select(Order).where(Order.id == order_id))
        return res.scalar_one_or_none()
