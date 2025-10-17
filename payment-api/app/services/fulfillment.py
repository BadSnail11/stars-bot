from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, cast
from sqlalchemy.dialects.postgresql import JSONB

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

async def fulfill_order(session: AsyncSession, order: Order) -> Tuple[bool, str]:
    """
    Выполнить заказ через Fragment API.
    Возвращает (ok, msg) — для показа пользователю.
    """
    # Кого кредитуем:
    # 1) если recipient задан в заказе — отправляем туда,
    # 2) иначе берём username из заказа,
    # 3) если и там пусто — используем заглушку (ошибка).
    recipient = (order.recipient or order.username or "").strip()
    if not recipient:
        msg = "Не указан получатель (username). Обратитесь в поддержку."
        await _save_result(session, order.id, False, msg, {"error": "missing recipient"})
        return False, msg

    try:
        if order.type == "stars":
            qty = int(order.amount or 0)
            if qty <= 0:
                raise ValueError("empty stars qty")
            data = await buy_stars(recipient=recipient, quantity=qty)
            msg = f"⭐ Успешно начислено: {qty} звёзд(ы) для {recipient}"
            await _save_result(session, order.id, True, msg, data)
            return True, msg

        elif order.type == "premium":
            months = int(order.amount or 0)
            if months <= 0:
                raise ValueError("empty months")
            data = await buy_premium(recipient=recipient, months=months)
            msg = f"👑 Premium активирован на {months} мес. для {recipient}"
            await _save_result(session, order.id, True, msg, data)
            return True, msg
        elif order.type == "ton":
            amount = int(order.amount or 0)
            if amount <= 0:
                raise ValueError("empty ton")
            data = await buy_ton(recipient=recipient, amount=amount)
            msg = f"Зачислено {amount} TON для {recipient}"
            await _save_result(session, order.id, True, msg, data)
            return True, msg

        else:
            msg = f"Неизвестный тип заказа: {order.type}"
            await _save_result(session, order.id, False, msg, {"error": "unknown type"})
            return False, msg

    except Exception as e:
        # сюда попадём, если Fragment API вернул 4xx/5xx или ошибка сети/валидации
        err = {"error": str(e)}
        msg = f"❌ Не удалось выполнить заказ через Fragment: {e}"
        await _save_result(session, order.id, False, msg, err)
        return False, msg
