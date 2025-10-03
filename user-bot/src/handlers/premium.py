# src/handlers/premium.py
from aiogram import Router, F, types
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from decimal import Decimal
import os, asyncio

from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..services.pricing import (
    get_premium_price_in_rub, calc_rub_for_premium,
    get_premium_price_in_ton, calc_ton_for_premium
)
from ..services.ton import wait_ton_payment
from ..services.platega import create_sbp_invoice, wait_payment_confirmed
from ..keyboards.common import who_kb, cancel_kb, main_menu_kb, payment_methods_kb, premium_duration_kb

class BuyPremium(StatesGroup):
    choose_target = State()
    enter_recipient = State()
    enter_months = State()
    choose_payment = State()

BTN_SELF   = "buy_premium_self"
BTN_GIFT   = "buy_premium_gift"
BTN_CANCEL = "buy_premium_cancel"

BTN_M3  = "prem_m3"
BTN_M6  = "prem_m6"
BTN_M12 = "prem_m12"

BTN_PAY_SBP   = "pay_premium_sbp"
BTN_PAY_TON   = "pay_premium_ton"
BTN_PAY_OTHER = "pay_premium_other"

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="premium")

    @router.message(F.text == ("👑 Премиум"))
    async def entry(m: types.Message, state: FSMContext):
        await state.clear()
        await state.set_state(BuyPremium.choose_target)
        await m.answer("Кому покупаем Telegram Premium?", reply_markup=who_kb(BTN_SELF, BTN_GIFT, BTN_CANCEL))

    @router.callback_query(F.data == BTN_CANCEL)
    async def cancel(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await cb.message.edit_text("Отменено. Возвращаемся в меню.")
        await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())

    @router.callback_query(F.data == BTN_SELF)
    async def choose_self(cb: types.CallbackQuery, state: FSMContext):
        await state.update_data(recipient=None)
        await state.set_state(BuyPremium.enter_months)
        await cb.message.edit_text("Выберите срок подписки:",
            reply_markup=premium_duration_kb(BTN_M3, BTN_M6, BTN_M12, BTN_CANCEL))

    @router.callback_query(F.data == BTN_GIFT)
    async def choose_gift(cb: types.CallbackQuery, state: FSMContext):
        await state.set_state(BuyPremium.enter_recipient)
        await cb.message.edit_text("Введите получателя (например, @username).", reply_markup=cancel_kb(BTN_CANCEL))

    @router.message(BuyPremium.enter_recipient)
    async def get_recipient(m: types.Message, state: FSMContext):
        text = (m.text or "").strip()
        if not text:
            await m.answer("Пусто. Укажите получателя, например, @username", reply_markup=cancel_kb(BTN_CANCEL))
            return
        await state.update_data(recipient=text)
        await state.set_state(BuyPremium.enter_months)
        await m.answer("Выберите срок подписки:",
            reply_markup=premium_duration_kb(BTN_M3, BTN_M6, BTN_M12, BTN_CANCEL))

    async def _set_months_and_ask_payment(cb: types.CallbackQuery, state: FSMContext, months: int):
        await state.update_data(months=months)
        await state.set_state(BuyPremium.choose_payment)
        await cb.message.edit_text(
            f"Premium на {months} мес.\nВыберите способ оплаты:",
            reply_markup=payment_methods_kb(BTN_PAY_SBP, BTN_PAY_TON, BTN_PAY_OTHER, BTN_CANCEL)
        )

    @router.callback_query(F.data == BTN_M3)
    async def months3(cb: types.CallbackQuery, state: FSMContext):
        await _set_months_and_ask_payment(cb, state, 3)

    @router.callback_query(F.data == BTN_M6)
    async def months6(cb: types.CallbackQuery, state: FSMContext):
        await _set_months_and_ask_payment(cb, state, 6)

    @router.callback_query(F.data == BTN_M12)
    async def months12(cb: types.CallbackQuery, state: FSMContext):
        await _set_months_and_ask_payment(cb, state, 12)

    # ====== СБП (Platega, RUB) ======
    @router.callback_query(F.data == BTN_PAY_SBP)
    async def pay_sbp(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        months = data.get("months")
        recipient = data.get("recipient")
        if not months:
            await cb.message.answer("Не вижу количество месяцев. Начните заново: «👑 Премиум».")
            await state.clear()
            return

        # пользователь + цена в RUB
        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(cb.from_user)

            price_per_month_rub = await get_premium_price_in_rub(session)
            amount_rub = calc_rub_for_premium(months, price_per_month_rub)

        # инвойс Platega
        payload = f"user:{cb.from_user.id}|premium:{months}"
        tx_id, redirect = await create_sbp_invoice(
            amount_rub=amount_rub,
            description=f"Telegram Premium {months} мес.",
            payload=payload
        )

        # заказ pending (RUB)
        async with session_maker() as session:
            orders = OrdersRepo(session)
            order = await orders.create_pending_sbp_order(
                user_id=user.id, 
                username=user.username,
                recipient=recipient,
                type="premium",
                amount=months,
                price=amount_rub,
                transaction_id=tx_id,
                redirect_url=redirect
            )

        await state.clear()
        await cb.message.edit_text(
            f"Заказ №{order.id}: Premium {months} мес. на {amount_rub} RUB\n"
            "🏦 СБП — платёж создан.\n"
            f"Ссылка на оплату: {redirect}\n\n"
            "Откройте ссылку и оплатите в течение 15 минут."
        )

        async def _poll():
            status_tx = await wait_payment_confirmed(tx_id)
            if status_tx:
                async with session_maker() as session:
                    orders = OrdersRepo(session)
                    await orders.mark_paid(order.id, tx_hash=status_tx, income=None)
                await cb.message.answer(f"✅ Оплата за заказ №{order.id} получена!")
                # TODO: активировать премиум себе/получателю
            else:
                await cb.message.answer(f"⏳ Заказ №{order.id}: время ожидания истекло или платёж отменён.")
        asyncio.create_task(_poll())

    # ====== TON (крипта) ======
    @router.callback_query(F.data == BTN_PAY_TON)
    async def pay_ton(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        months = data.get("months")
        recipient = data.get("recipient")
        wallet = os.getenv("TON_WALLET")
        if not months or not wallet:
            await cb.message.answer("TON кошелёк не настроен или нет количества. Попробуйте ещё раз.")
            await state.clear()
            return

        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            user = await users.upsert_from_telegram(cb.from_user)

            price_per_month_ton = await get_premium_price_in_ton(session)
            total_ton = calc_ton_for_premium(months, price_per_month_ton)

            memo_prefix = os.getenv("TON_MEMO_PREFIX", "INV-")
            # для читаемости укажем тип P (premium)
            memo = f"{memo_prefix}P-{cb.from_user.id}-{cb.message.message_id}"

            order = await orders.create_pending_ton_order(
                user_id=user.id, 
                username=user.username,
                recipient=recipient,
                type="premium",
                amount=months,
                price=float(total_ton),
                memo=memo,
                wallet=wallet
            )

        await state.clear()
        await cb.message.edit_text(
            f"Заказ №{order.id}: Premium {months} мес."
            "💎 Платёж (TON)\n"
            f"➤ Адрес: <code>{wallet}</code>\n"
            f"➤ Сумма: <code>{total_ton}</code> TON\n"
            f"➤ Комментарий (TAG/MEMO): <code>{memo}</code>\n\n"
        )

        async def _check():
            tx_hash = await wait_ton_payment(wallet, memo, total_ton)
            if tx_hash:
                async with session_maker() as session:
                    orders = OrdersRepo(session)
                    await orders.mark_paid(order.id, tx_hash, income=None)
                await cb.message.answer(f"✅ Оплата за заказ №{order.id} получена!\nTX: <code>{tx_hash}</code>")
                # TODO: активировать премиум себе/получателю
            else:
                await cb.message.answer(f"⏳ Заказ №{order.id}: время ожидания истекло. Платёж не найден.")
        asyncio.create_task(_check())

    # ====== Другая крипта — заглушка ======
    @router.callback_query(F.data == BTN_PAY_OTHER)
    async def pay_other(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await cb.message.edit_text("🪙 Другие криптовалюты появятся позже. Выберите пока СБП или TON.")

    return router
