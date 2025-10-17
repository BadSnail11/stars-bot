import os
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, cast
from sqlalchemy.dialects.postgresql import JSONB

from ..models import Order
from ..repositories.users import UsersRepo
from ..repositories.referrals import ReferralsRepo

from ..services.converter import get_amount

# def _pct() -> Decimal:
#     try:
#         return Decimal(os.getenv("REFERRAL_PERCENT", "5"))
#     except Exception:
#         return Decimal("5")

async def accrue_referral_reward(session: AsyncSession, order: Order, bot_id: int) -> None:
    """
    Начисляет реферальную награду пригласившему пользователя, оформившего заказ.
    Баланс храним в TON-эквиваленте (users.balance).
    """
    # находим пригласившего
    refs = ReferralsRepo(session)
    referrer_id = await refs.get_referrer_id_by_referee(order.user_id)
    print("ref_id:", referrer_id)
    if not referrer_id:
        return  # нет реферера — нечего делать

    # считаем награду: price * pct
    # pct = _pct()
    # if not order.price or pct <= 0:
    #     return
    # base_amount = Decimal(str(order.price)) * (pct / Decimal("100"))

    amount = await get_amount(session, order, bot_id)
    print("amount:", amount)

    # конвертируем в TON при необходимости
    # reward_ton = await convert_amount_to_ton(session, base_amount, order.currency or "TON")

    # обновляем баланс пригласившего
    users = UsersRepo(session)
    await users.add_balance(referrer_id, float(amount))

    # опционально: положим след в payload заказа
    # from sqlalchemy import update
    # from ..models import Order as OrderModel
    # new_kv = cast(
    #     {
    #         "referral": {
    #             "referrer_id": referrer_id,
    #             # "percent": float(pct),
    #             "reward": float(amount),
    #         }
    #     },
    #     JSONB,
    # )
    # merged = func.coalesce(OrderModel.gateway_payload, cast({}, JSONB)).op("||")(new_kv)
    # await session.execute(
    #     update(OrderModel)
    #     .where(OrderModel.id == order.id)
    #     .values(gateway_payload=merged)
    # )
    # await session.commit()
