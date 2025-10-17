import os, aiohttp
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

from app.repositories.withdrawals import WithdrawalsRepo
from app.services.heleket import create_withdraw

MIN = Decimal(os.getenv("WITHDRAW_MIN", "0.5"))
MAX = Decimal(os.getenv("WITHDRAW_MAX", "100000"))

class WithdrawalLogicError(Exception): ...

async def _get_user_balance(s: AsyncSession, user_id: int) -> Decimal:
    row = (await s.execute(text("SELECT balance FROM users WHERE id=:id"), {"id": user_id})).first()
    if not row: raise WithdrawalLogicError("user not found")
    return Decimal(row[0] or 0)
 5.000000 U
async def _add_user_balance(s: AsyncSession, user_id: int, delta: Decimal):
    await s.execute(text("UPDATE users SET balance = balance + :d WHERE id=:id"), {"id": user_id, "d": str(delta)})

async def request_withdrawal(s: AsyncSession, user_id: int, to_address: str, amount: Decimal, network: str) -> dict:
    """
    Основной сценарий:
    1) валидация суммы
    2) проверка баланса
    3) создаём withdrawal (pending)
    4) (опц.) оцениваем комиссию
    5) списываем amount с баланса (reserve)
    6) создаём выплату в Heleket -> status processing
    """
    if amount < MIN: raise WithdrawalLogicError(f"Минимальная сумма: {MIN} USDT")
    if amount > MAX: raise WithdrawalLogicError(f"Превышен лимит: {MAX} USDT")

    # баланс
    balance = await _get_user_balance(s, user_id)
    if balance < amount:
        raise WithdrawalLogicError("Недостаточно средств на балансе")

    repo = WithdrawalsRepo(s)
    wid = await repo.create(user_id=user_id, amount=float(amount), to_address=to_address, currency="USDT")

    await _add_user_balance(s, user_id, delta=-amount)

    # создаём выплату в Heleket
    response = await create_withdraw(order_id=str(wid), to_address=to_address, amount=str(amount), network=network)

    await repo.set_processing(wid, str(wid), response)
    await s.commit()

    return {
        "withdrawal_id": wid,
        "amount": str(amount),
        "status": "processing",
    }

async def apply_withdrawal_status(s: AsyncSession, provider_id: str, provider_status: str, payload: dict) -> None:
    """
    Проставляет конечный статус и при необходимости делает финдействия.
    mapping статусов подгони под ответ Heleket.
    """
    repo = WithdrawalsRepo(s)
    # найдём наш withdrawal
    wid = await repo.get_by_provider(provider_id)
    if not wid:
        # ничего не делаем — нет записи
        return

    status_map = {
        "completed": "sent",
        "success":   "sent",
        "processing":"processing",
        "failed":    "failed",
        "canceled":  "canceled",
    }
    status = status_map.get(provider_status.lower(), "processing")

    # если failed/canceled — вернём деньги пользователю
    if status in ("failed", "canceled"):
        # узнаем сумму
        row = (await s.execute(text("SELECT user_id, amount FROM withdrawals WHERE id=:id"), {"id": wid})).first()
        if row:
            uid, amt = int(row[0]), Decimal(str(row[1] or "0"))
            await _add_user_balance(s, uid, delta=amt)

    await repo.mark_status(wid, status, payload)
    await s.commit()
