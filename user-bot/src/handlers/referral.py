# src/handlers/referral.py
from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..services.referral import build_ref_link
from ..keyboards.common import main_menu_kb, back_nav_kb, network_kb, accept_kb  # если у тебя есть главное меню
from ..repositories.users import UsersRepo
import os
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from ..services.payments_api import create_withdraw

_min_balace = int(os.getenv("MIN_BALANCE", "5"))

class Referral(StatesGroup):
    enter_amount = State()
    enter_wallet = State()
    enter_net = State()
    enter_address = State()
    accept_withdraw = State()

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="referral")

    @router.callback_query(F.data == "referal")
    async def show_ref_link(cb: types.CallbackQuery):
        m = cb.message
        me = await m.bot.get_me()
        link = build_ref_link(me.username or "", m.from_user.id)

        async with session_maker() as s:
            users = UsersRepo(s)
            user = await users.get_by_tg_id(m.chat.id)

        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🔗 Открыть ссылку", url=link))
        kb.row(types.InlineKeyboardButton(text="Вывод средств", callback_data="withdraw"))
        kb.row(types.InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu"))
        markup = kb.as_markup()

        text = (
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей по вашей ссылке и получайте 40% прибыли от их оплат.\n\n"
            f"Ваш баланс: {user.balance} USD\n\n"
            f"Ваша ссылка:\n<code>{link}</code>"
        )
        await m.edit_text(text, reply_markup=markup)

    # опционально: обработчик «назад в меню»
    @router.callback_query(lambda c: c.data == "back_to_menu")
    async def back_to_menu(cb: types.CallbackQuery):
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
        await cb.answer()

    @router.callback_query(F.data == "withdraw")
    async def withdraw(cb: types.CallbackQuery, state: FSMContext):
        print(1)
        m = cb.message
        
        async with session_maker() as s:
            users = UsersRepo(s)
            user = await users.get_by_tg_id(m.chat.id)
            balance = user.balance

        print(balance)
        
        if balance < _min_balace:
            await m.edit_text(text=f"Вывод доступен от {_min_balace} USD", reply_markup=back_nav_kb())
            return

        await m.edit_text(text=f"Введите количество USD на вывод (не меньше {_min_balace} USD):", reply_markup=back_nav_kb())
        await state.set_state(Referral.enter_amount)

    @router.message(Referral.enter_amount)
    async def enter_amount(m: types.Message, state: FSMContext):
        try:
            amount = float(m.text)
        except:
            await m.answer("На ввод ожидается число!", reply_markup=back_nav_kb())
            await state.clear()
            return
        
        if amount < _min_balace:
            await m.answer(f"Сумма должна быть больше {_min_balace}", reply_markup=back_nav_kb())
            await state.clear()
            return
        
        await state.update_data(amount=amount)
        
        await m.answer(text=f"Выберите сеть:", reply_markup=network_kb())
        # await context.set_state(Referral.enter_network)
    
    @router.callback_query(F.data.split("_")[0] == "NET")
    async def choose_net(cb: types.CallbackQuery, state: FSMContext):
        net = cb.data.split("_")[1]
        await state.update_data(net=net)
        m = cb.message
        await m.edit_text("Введите Адрес своего кошелька (ВАЖНО, не допустите ошибку в адресе кошелька, иначе средства поступят не на тот адрес БЕЗВОЗВРАТНО):", reply_markup=back_nav_kb())
        await state.set_state(Referral.enter_address)

    @router.message(Referral.enter_address)
    async def enter_address(m: types.Message, state: FSMContext):
        address = m.text
        await state.update_data(address=address)
        data = await state.get_data()
        amount = data.get("amount")
        net = data.get("net")
        await m.answer(text=f"Подтвердите ваши данные:\n"
                 f"Сумма: {amount} USTD\n"
                 f"Сеть: {net}\n"
                 f"Адрес: {address}", reply_markup=accept_kb())
        await state.set_state(Referral.accept_withdraw)

    @router.callback_query(F.data == "accept")
    async def choose_net(cb: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        address = str(data.get("address"))
        amount = float(data.get("amount"))
        net = str(data.get("net"))
        m = cb.message

        async with session_maker() as s:
            users = UsersRepo(s)
            user = await users.get_by_tg_id(m.chat.id)

        user_id = user.id

        print(m.chat.id, address, amount, net)
        
        try:
            res = await create_withdraw(int(user_id), address, amount)
            tx = res["tx"]
            await m.edit_text("Запрос на вывод был отправлен. Ожидайте поступления средств", reply_markup=back_nav_kb())
        except:
            await m.edit_text("Извините, в процессе вывода произошла ошибка. Попробуйте позже", reply_markup=back_nav_kb())

        await state.clear()

    return router
