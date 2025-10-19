from aiogram import Router, F, types
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from decimal import Decimal
import os, asyncio

from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..repositories.user_bots import UserBotsRepo
from ..keyboards.common import who_kb, cancel_kb, main_menu_kb, payment_methods_kb, payment_kb, back_nav_kb

from ..services.payments_api import create_order
from ..services.order_poll import poll_until_paid

class BuyStars(StatesGroup):
    choose_target = State()
    enter_me = State()
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
    @router.callback_query(F.data == "stars")
    async def entry(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await state.set_state(BuyStars.choose_target)
        await cb.message.edit_text("Кому покупаем звёзды?", reply_markup=who_kb(BTN_SELF, BTN_GIFT, BTN_CANCEL))

    # Отмена
    @router.callback_query(F.data == BTN_CANCEL)
    async def cancel(cb: types.CallbackQuery, state: FSMContext):
        await state.clear()
        # await cb.message.edit_text("Отменено. Возвращаемся в меню.")
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())

    # Себе
    @router.callback_query(F.data == BTN_SELF)
    async def choose_self(cb: types.CallbackQuery, state: FSMContext):
        user = (await cb.bot.get_chat_member(cb.message.chat.id, cb.message.chat.id)).user
        if not user.username:
            await state.set_state(BuyStars.enter_me)
            await cb.message.edit_text("У вас скрыт юзернейм, введите вручную:", reply_markup=back_nav_kb())
            return
        await state.update_data(recipient=None)
        await state.set_state(BuyStars.enter_qty)
        await cb.message.edit_text("Сколько звёзд купить? (минимум 50)", reply_markup=back_nav_kb())

    @router.message(BuyStars.enter_me)
    async def get_me(m: types.Message, state: FSMContext):
        text = (m.text or "").strip()
        if not text:
            await m.answer("Пустое значение. Укажите получателя, например, @username", reply_markup=cancel_kb(BTN_CANCEL))
            return
        await state.update_data(recipient=text)
        await state.set_state(BuyStars.enter_qty)
        await m.answer("Сколько звёзд купить? (минимум 50)", reply_markup=cancel_kb(BTN_CANCEL))

    
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

    async def _start_polling(cb: types.CallbackQuery, order_id: int):
        async def _on_paid(data: dict):
            msg = data.get("message") or "Оплата подтверждена."
            await cb.message.answer(f"✅ Заказ №{order_id} завершён!\n{msg}", reply_markup=back_nav_kb())

        async def _on_timeout():
            await cb.message.answer(f"⏳ Заказ №{order_id}: время ожидания истекло.", reply_markup=back_nav_kb())

        asyncio.create_task(poll_until_paid(order_id, on_paid=_on_paid, on_timeout=_on_timeout, interval_sec=15, timeout_sec=30 * 60))

    @router.callback_query(F.data == BTN_PAY_TON)
    async def pay_ton(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        qty = data.get("qty")
        recipient = data.get("recipient")
        if not qty:
            await cb.message.answer("Не вижу количество. Начните заново: «⭐ Купить звёзды».")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="stars",
            amount=int(qty),
            payment_method="TON",
            bot_tg_id=cb.bot.id
        )
        order_id = resp["order_id"]
        ton = resp.get("ton", {})
        address = ton.get("address")
        memo = ton.get("memo")
        amount_ton = ton.get("amount_ton")
        # print(amount_ton)
        link = f"ton://transfer/{address}?amount={int(float(amount_ton) * 1000000)}000&text={memo}"

        await state.clear()
        await cb.message.edit_text(
            "💎 Платёж (TON)\n"
            f"Заказ №{order_id}: {qty} ⭐\n\n"
            f"Переведите <code>{amount_ton}</code> TON на адрес:\n"
            f"<code>{address}</code>\n\n"
            f"❗️ Обязательно укажите комментарий (TAG/MEMO):\n"
            f"<code>{memo}</code>\n\n"
            f"Если вы не укажите комментарий - ваш депозит не будет зачислен\n\n"
            f"Счет для оплаты действителен 30 минут",
            reply_markup=payment_kb(link)
        )
        await _start_polling(cb, order_id)


    @router.callback_query(F.data == BTN_PAY_SBP)
    async def pay_sbp(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        qty = data.get("qty")
        recipient = data.get("recipient")
        if not qty:
            await cb.message.answer("Не вижу количество. Начните заново: «⭐ Купить звёзды»")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="stars",
            amount=int(qty),
            payment_method="SBP",
            bot_tg_id=cb.bot.id
        )
        order_id = resp["order_id"]
        sbp = resp.get("sbp", {})
        redirect = sbp.get("redirect_url")
        amount_rub = sbp.get("amount_rub")

        await state.clear()
        await cb.message.edit_text(
            "🏦 Платёж СБП\n"
            f"Заказ №{order_id}: {qty} ⭐\n\n"
            "Нажмите на копку <b>Оплатить</b> для перехода к оплате\n\n"
            "Либо перейдите по ссылке:\n"
            f"<code>{redirect}</code>\n\n"
            "Счет для оплаты действителен 30 минут",
            reply_markup=payment_kb(redirect)
        )
        await _start_polling(cb, order_id)

    @router.callback_query(F.data == BTN_PAY_OTHER)  # «Другая крипта» → HELEKET
    async def pay_heleket(cb: types.CallbackQuery, state):
        data = await state.get_data()
        qty = data.get("qty")
        recipient = data.get("recipient")
        if not qty:
            await cb.message.answer("Не вижу количество. Начните заново: «⭐ Купить звёзды».")
            await state.clear()
            return

        resp = await create_order(
            user_tg_id=cb.from_user.id,
            username=cb.from_user.username,
            recipient=recipient,
            order_type="stars",
            amount=int(qty),
            payment_method="CRYPTO_OTHER",
            bot_tg_id=cb.bot.id
        )
        order_id = resp["order_id"]
        url = resp["other"]["redirect_url"]
        # msg = resp.get("message") or "Счёт Heleket создан. Перейдите по ссылке на странице оплаты."

        await state.clear()
        await cb.message.edit_text(f"🪙 Платёж Heleket\n"
                                    f"Заказ №{order_id}: {qty} ⭐\n\n"
                                    "Нажмите на копку <b>Оплатить</b> для перехода к оплате\n\n"
                                    "Либо перейдите по ссылке:\n"
                                    f"<code>{url}</code>\n\n"
                                    "Счет для оплаты действителен 30 минут",
                                    reply_markup=payment_kb(url))
        # Если хочешь показать URL сразу здесь — расширь ответ Payment API (добавь поле heleket.url)
        await _start_polling(cb, order_id)
        
    return router
