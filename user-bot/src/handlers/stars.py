from aiogram import Router, F, types
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from decimal import Decimal
import os, asyncio

from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..services.pricing import get_star_price_in_ton, calc_ton_for_stars, get_star_price_in_rub, calc_rub_for_stars
from ..services.ton import wait_ton_payment
from ..services.platega import create_sbp_invoice, wait_payment_confirmed
from ..keyboards.common import who_kb, cancel_kb, main_menu_kb, payment_methods_kb

class BuyStars(StatesGroup):
    choose_target = State()
    enter_recipient = State()
    enter_qty = State()
    choose_payment = State()

BTN_SELF = "buy_stars_self"
BTN_GIFT = "buy_stars_gift"
BTN_CANCEL = "buy_stars_cancel"


BTN_PAY_SBP   = "pay_sbp"
BTN_PAY_TON   = "pay_ton"
BTN_PAY_OTHER = "pay_other"

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
        
        await state.update_data(qty=qty)
        await state.set_state(BuyStars.choose_payment)
        await m.answer(
            f"Окей, {qty} ⭐.\nВыберите способ оплаты:",
            reply_markup=payment_methods_kb(BTN_PAY_SBP, BTN_PAY_TON, BTN_PAY_OTHER, BTN_CANCEL)
        )

    @router.callback_query(F.data == BTN_PAY_TON)
    async def pay_ton(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        qty = data.get("qty")
        recipient = data.get("recipient")
        wallet = os.getenv("TON_WALLET")
        if not qty or not wallet:
            await cb.message.answer("TON кошелёк не настроен или нет количества. Попробуйте ещё раз.")
            await state.clear()
            return

        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(cb.from_user)

            price_per_star_ton = await get_star_price_in_ton(session)
            total_ton = calc_ton_for_stars(qty, price_per_star_ton)

            memo_prefix = os.getenv("TON_MEMO_PREFIX", "INV-")
            memo = f"{memo_prefix}{cb.from_user.id}-{cb.message.message_id}"

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
        await cb.message.edit_text(
            f"Заказ №{order.id}: {qty} ⭐"
            "💎 Платёж (TON)\n"
            f"➤ Адрес: <code>{wallet}</code>\n"
            f"➤ Сумма: <b>{total_ton}</b> TON\n"
            f"➤ Комментарий (TAG/MEMO): <code>{memo}</code>\n\n"   
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

    @router.callback_query(F.data == BTN_PAY_SBP)
    async def pay_sbp(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        qty = data.get("qty")
        recipient = data.get("recipient")
        if not qty:
            await cb.message.answer("Не вижу количество. Начните заново: «⭐ Купить звёзды».")
            await state.clear()
            return

        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(cb.from_user)

            # RUB-цена
            price_per_star_rub = await get_star_price_in_rub(session)
            amount_rub = calc_rub_for_stars(qty, price_per_star_rub)

        # создаём счёт в Platega
        payload = f"user:{cb.from_user.id}|stars:{qty}"
        tx_id, redirect = await create_sbp_invoice(
            amount_rub=amount_rub,
            description=f"Покупка {qty}⭐",
            payload=payload
        )

        # пишем заказ в БД (pending)
        async with session_maker() as session:
            orders = OrdersRepo(session)
            order = await orders.create_pending_sbp_order(
                user_id=user.id,
                username=user.username,
                recipient=recipient,
                type="stars",
                amount=qty,
                price=float(amount_rub),
                transaction_id=tx_id,
                redirect_url=redirect
            )

        await state.clear()
        await cb.message.edit_text(
            f"Заказ №{order.id}: {qty} ⭐ на {amount_rub} RUB\n"
            "🏦 СБП — платёж создан.\n"
            f"Ссылка на оплату: {redirect}\n\n"
            "Откройте ссылку, отсканируйте QR и оплатите в течение 15 минут."
        )

        async def _poll():
            status_tx = await wait_payment_confirmed(tx_id)
            if status_tx:
                async with session_maker() as session:
                    orders = OrdersRepo(session)
                    await orders.mark_paid(order.id, tx_hash=status_tx, income=None)
                await cb.message.answer(f"✅ Оплата по заказу №{order.id} получена!")
                # TODO: тут начислим звёзды/подарок
            else:
                await cb.message.answer(f"⏳ Заказ №{order.id}: время ожидания истекло или платёж отменён.")

        asyncio.create_task(_poll())
        
    return router
