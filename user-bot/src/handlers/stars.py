from aiogram import Router, F, types
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from decimal import Decimal
import os, asyncio

from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..services.pricing import get_star_price_in_ton, calc_ton_for_stars
from ..services.ton import wait_ton_payment
from ..keyboards.common import who_kb, cancel_kb, main_menu_kb

class BuyStars(StatesGroup):
    choose_target = State()
    enter_recipient = State()
    enter_qty = State()

BTN_SELF = "buy_stars_self"
BTN_GIFT = "buy_stars_gift"
BTN_CANCEL = "buy_stars_cancel"

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="stars")

    # Точка входа — пункт меню "⭐ Купить звёзды"
    @router.message(F.text == ("⭐ Купить звёзды"))
    async def entry(m: types.Message, state: FSMContext):
        await state.clear()
        await state.set_state(BuyStars.choose_target)
        await m.answer("Кому покупаем звёзды?", reply_markup=who_kb(BTN_SELF, BTN_GIFT, BTN_CANCEL))

    # Отмена
    @router.callback_query(F.data == BTN_CANCEL)
    async def cancel(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await cb.message.edit_text("Отменено. Возвращаемся в меню.")
        await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())

    # Себе
    @router.callback_query(F.data == BTN_SELF)
    async def choose_self(cb: types.CallbackQuery, state: FSMContext):
        await state.update_data(recipient=None)
        await state.set_state(BuyStars.enter_qty)
        await cb.message.edit_text("Сколько звёзд купить? (минимум 50)")
    
    # Подарок
    @router.callback_query(F.data == BTN_GIFT)
    async def choose_gift(cb: types.CallbackQuery, state: FSMContext):
        await state.set_state(BuyStars.enter_recipient)
        await cb.message.edit_text("Введите получателя (например, @username).", reply_markup=cancel_kb(BTN_CANCEL))

    # Получатель текстом
    @router.message(BuyStars.enter_recipient)
    async def get_recipient(m: types.Message, state: FSMContext):
        text = (m.text or "").strip()
        if not text:
            await m.answer("Пустое значение. Укажите получателя, например, @username", reply_markup=cancel_kb(BTN_CANCEL))
            return
        await state.update_data(recipient=text)
        await state.set_state(BuyStars.enter_qty)
        await m.answer("Сколько звёзд купить? (минимум 50)", reply_markup=cancel_kb(BTN_CANCEL))

    # Количество звёзд
    @router.message(BuyStars.enter_qty)
    async def get_qty(m: types.Message, state: FSMContext):
        try:
            qty = int((m.text or "").strip())
        except Exception:
            await m.answer("Введите целое число. Пример: 100", reply_markup=cancel_kb(BTN_CANCEL))
            return
        if qty < 50:
            await m.answer("Минимум 50. Укажите количество ≥ 50.", reply_markup=cancel_kb(BTN_CANCEL))
            return

        data = await state.get_data()
        recipient = data.get("recipient")

        wallet = os.getenv("TON_WALLET")
        if not wallet:
            await m.answer("Кошелёк TON не настроен. Обратитесь в поддержку.")
            await state.clear()
            return

        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(m.from_user)

            # цена 1 звезды в TON
            price_per_star_ton = await get_star_price_in_ton(session)  # Decimal
            total_ton = calc_ton_for_stars(qty, price_per_star_ton)    # Decimal

            memo_prefix = os.getenv("TON_MEMO_PREFIX", "INV-")
            memo = f"{memo_prefix}{m.from_user.id}-{m.message_id}"

            # создаём заказ pending
            # order = await orders.create_pending_ton_order(
            #     user_id=user.id,
            #     username=user.username,
            #     stars_qty=qty,
            #     recipient=recipient,
            #     amount_ton=float(total_ton),
            #     memo=memo,
            #     wallet=wallet,
            # )
            order = await orders.create_pending_ton_order(
                user_id=user.id,
                username=user.username,
                recipient=recipient,
                type="stars",
                amount=qty,
                price=float(total_ton),
                memo=memo,
                wallet=wallet
            )

        await state.clear()
        await m.answer(
            f"Заказ №{order.id}: {qty} ⭐\n"
            "🔐 Платёж (TON)\n"
            f"➤ Адрес: <code>{wallet}</code>\n"
            f"➤ Сумма: <code>{total_ton}</code> TON\n"
            f"➤ Комментарий (TAG/MEMO): <code>{memo}</code>\n\n"
            "Важно: укажите комментарий <b>точно</b>, иначе платёж не будет найден автоматически.",
            disable_web_page_preview=True
        )

        # Фоновая проверка платежа — без блокировки обработчика
        async def _check():
            tx_hash = await wait_ton_payment(wallet, memo, total_ton)
            if tx_hash:
                async with session_maker() as session:
                    orders = OrdersRepo(session)
                    await orders.mark_paid(order.id, tx_hash, income=None)
                await m.answer(f"✅ Оплата за заказ №{order.id} получена!\nTX: <code>{tx_hash}</code>")
                # здесь позже добавим логику начисления звёзд/подарка
            else:
                await m.answer(f"⏳ Заказ №{order.id}: время ожидания истекло. Платёж не найден.")

        asyncio.create_task(_check())

    return router
