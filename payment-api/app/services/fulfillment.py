from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, cast
from sqlalchemy.dialects.postgresql import JSONB
import asyncio
from ..redis import get_queue
from ..db import SessionLocal

from ..repositories.orders import OrdersRepo
from ..models import Order
from .fragment import buy_stars, buy_premium, buy_ton

async def _save_result(session: AsyncSession, order_id: int, ok: bool, text: str, result_json: dict | None):
    # message — для пользователя; gateway_payload.result — сырой ответ API
    new_payload = cast({"fulfillment_result": result_json or {}}, JSONB)
    merged = func.coalesce(Order.gateway_payload, cast({}, JSONB)).op("||")(new_payload)

    await session.execute(
        update(Order)
        .where(Order.id == order_id)
        .values(
            message=text,
            gateway_payload=merged,
        )
    )
    await session.commit()

def task_wrapper(order_id):
    asyncio.run(fulfill_order(order_id))
    print(f"Done: {order_id}")

async def fulfill_order(order_id: int) -> Tuple[bool, str]:
    """
    Выполнить заказ через Fragment API.
    Возвращает (ok, msg) — для показа пользователю.
    """
    # Кого кредитуем:
    # 1) если recipient задан в заказе — отправляем туда,
    # 2) иначе берём username из заказа,
    # 3) если и там пусто — используем заглушку (ошибка).
    # recipient = (order.recipient or order.username or "").strip()
    async with SessionLocal() as session:
        orders = OrdersRepo(session)
        order = await orders.get_by_id(order_id)
        if order.recipient:
            recipient = order.recipient[1::].strip()
        else:
            recipient = order.username.strip()
        if not recipient:
            msg = "Не указан получатель (username). Обратитесь в поддержку."
            await _save_result(session, order.id, False, msg, {"error": "missing recipient"})
            return False, msg

        try:
            print(2/0)
            print(4)
            if order.type == "stars":
                qty = int(order.amount or 0)
                if qty <= 0:
                    raise ValueError("empty stars qty")
                data = await buy_stars(query=recipient, quantity=qty)
                msg = f"⭐ Успешно начислено: {qty} звёзд(ы) для {recipient}"
                await _save_result(session, order.id, True, msg, data)
                return True, msg

            elif order.type == "premium":
                months = int(order.amount or 0)
                if months <= 0:
                    raise ValueError("empty months")
                data = await buy_premium(query=recipient, months=months)
                msg = f"👑 Premium активирован на {months} мес. для {recipient}"
                await _save_result(session, order.id, True, msg, data)
                return True, msg
            elif order.type == "ton":
                amount = int(order.amount or 0)
                if amount <= 0:
                    raise ValueError("empty ton")
                data = await buy_ton(query=recipient, ton=amount)
                msg = f"Зачислено {amount} TON для {recipient}"
                await _save_result(session, order.id, True, msg, data)
                return True, msg

            else:
                msg = f"Неизвестный тип заказа: {order.type}"
                await _save_result(session, order.id, False, msg, {"error": "unknown type"})
                return False, msg

        except Exception as e:
            print(5)
            # сюда попадём, если Fragment API вернул 4xx/5xx или ошибка сети/валидации
            err = {"error": str(e)}
            msg = f"❌ Не удалось выполнить заказ через Fragment: {e}"
            await _save_result(session, order.id, False, msg, err)
            q = await get_queue()
            q.enqueue(task_wrapper, order_id)
            return False, msg
