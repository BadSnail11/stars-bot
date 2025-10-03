from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from decimal import Decimal
import os, asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..services.ton import wait_ton_payment


def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="crypto")

    @router.message(Command("buy_ton"))
    async def buy_ton(m: types.Message, command: CommandObject):
        # Парсим сумму
        if not command.args:
            await m.answer("Использование: <code>/buy_ton 0.5</code>")
            return
        try:
            amount_ton = Decimal(command.args.replace(",", "."))
            if amount_ton <= 0:
                raise ValueError()
        except Exception:
            await m.answer("Некорректная сумма. Пример: <code>/buy_ton 0.5</code>")
            return

        wallet = os.getenv("TON_WALLET")
        if not wallet:
            await m.answer("Кошелёк TON не настроен. Обратитесь в поддержку.")
            return

        memo_prefix = os.getenv("TON_MEMO_PREFIX", "INV-")
        memo = f"{memo_prefix}{m.from_user.id}-{m.message_id}"

        # Создаём pending-заказ
        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(m.from_user)
            order = await orders.create_pending_ton_order(user.id, user.username, float(amount_ton), memo, wallet)

        await m.answer(
            "🔐 Платёж (TON)\n"
            f"➤ Адрес: <code>{wallet}</code>\n"
            f"➤ Сумма: <b>{amount_ton}</b> TON\n"
            f"➤ Комментарий (TAG/MEMO): <code>{memo}</code>\n\n"
            "Важно: укажите комментарий <b>точно</b>, иначе платёж не будет найден автоматически.",
            disable_web_page_preview=True
        )

        # Фоновая проверка платежа
        async def _check():
            tx_hash = await wait_ton_payment(wallet, memo, amount_ton)
            if tx_hash:
                async with session_maker() as session:
                    orders = OrdersRepo(session)
                    await orders.mark_paid(order.id, tx_hash, income=None)
                await m.answer(f"✅ Платёж получен!\nTX: <code>{tx_hash}</code>")
            else:
                await m.answer("⏳ Время ожидания истекло. Платёж не найден.")

        asyncio.create_task(_check())

    return router
