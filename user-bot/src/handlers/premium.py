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
from ..keyboards.common import who_kb, cancel_kb, main_menu_kb, payment_methods_kb, premium_duration_kb

from ..services.payments_api import create_order
from ..services.order_poll import poll_until_paid

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

    @router.callback_query(F.data == ("premium"))
    async def entry(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await state.set_state(BuyPremium.choose_target)
        await cb.message.edit_text("Кому покупаем Telegram Premium?", reply_markup=who_kb(BTN_SELF, BTN_GIFT, BTN_CANCEL))

    @router.callback_query(F.data == BTN_CANCEL)
    async def cancel(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        # await cb.message.edit_text("Отменено. Возвращаемся в меню.")
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())

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

    async def _start_polling(cb: types.CallbackQuery, order_id: int):
        async def _on_paid(data: dict):
            msg = data.get("message") or "Оплата подтверждена."
            await cb.message.answer(f"✅ Премиум — заказ №{order_id} завершён!\n{msg}")
        async def _on_timeout():
            await cb.message.answer(f"⏳ Заказ №{order_id}: время ожидания истекло.")
        asyncio.create_task(poll_until_paid(order_id, on_paid=_on_paid, on_timeout=_on_timeout))

    # ====== СБП (Platega, RUB) ======
    @router.callback_query(F.data == BTN_PAY_SBP)
    async def pay_sbp(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        months = data.get("months")
        recipient = data.get("recipient")
        if not months:
            await cb.message.answer("Не вижу срок. Начните заново: «👑 Премиум».")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="premium",
            amount=int(months),
            payment_method="SBP",
        )
        order_id = resp["order_id"]
        sbp = resp.get("sbp", {})
        await state.clear()
        await cb.message.edit_text(
            "🏦 СБП — платёж создан.\n"
            f"Заказ №{order_id}: Premium {months} мес. на {sbp.get('amount_rub')} RUB\n"
            f"Ссылка на оплату: {sbp.get('redirect_url')}\n\n"
            "Оплатите в течение 15 минут."
        )
        await _start_polling(cb, order_id)

    # ====== TON (крипта) ======
    @router.callback_query(F.data == BTN_PAY_TON)
    async def pay_ton(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        months = data.get("months")
        recipient = data.get("recipient")
        if not months:
            await cb.message.answer("Не вижу срок. Начните заново: «👑 Премиум».")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="premium",
            amount=int(months),
            payment_method="TON",
        )
        order_id = resp["order_id"]
        ton = resp.get("ton", {})
        await state.clear()
        await cb.message.edit_text(
            "💎 Платёж (TON)\n"
            f"➤ Адрес: <code>{ton.get('address')}</code>\n"
            f"➤ Сумма: <b>{ton.get('amount_ton')}</b> TON\n"
            f"➤ Комментарий: <code>{ton.get('memo')}</code>\n\n"
            f"Заказ №{order_id}: Premium {months} мес."
        )
        await _start_polling(cb, order_id)

    # ====== Другая крипта — заглушка ======
    @router.callback_query(F.data == BTN_PAY_OTHER)  # HELEKET
    async def pay_heleket(cb: types.CallbackQuery, state):
        data = await state.get_data()
        months = data.get("months")
        recipient = data.get("recipient")
        if not months:
            await cb.message.answer("Не вижу срок. Начните заново: «👑 Премиум».")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="premium",
            amount=int(months),
            payment_method="CRYPTO_OTHER",
        )
        order_id = resp["order_id"]
        msg = resp.get("message") or "Счёт Heleket создан. Перейдите по ссылке на странице оплаты."
        await state.clear()
        await cb.message.edit_text(f"🪙 Heleket\nЗаказ №{order_id}: Premium {months} мес.\n{msg}")
        await _start_polling(cb, order_id)

    return router
