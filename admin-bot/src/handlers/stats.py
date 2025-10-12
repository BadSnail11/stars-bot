from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from src.db import SessionLocal
from src.utils.owner_scope import resolve_owner_and_bot_key
from src.models import User, Order

router = Router(name="stats_fsm")

class StatsStates(StatesGroup):
    waiting_choice = State()

def stats_kb():
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="👥 Пользователи"), types.KeyboardButton(text="💳 Оплаты")],
            [types.KeyboardButton(text="⬅️ Назад в меню")],
        ],
        resize_keyboard=True
    )
    return kb

@router.message(F.text == ("📊 Статистика"))
async def stats_enter(m: types.Message, state: FSMContext):
    await state.set_state(StatsStates.waiting_choice)
    await m.answer("Выберите метрику:", reply_markup=stats_kb())

@router.message(StatsStates.waiting_choice, F.text == ("👥 Пользователи"))
async def stats_users(m: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        cnt = (await s.execute(
            select(func.count()).select_from(User).where(User.bot_key == bot_key)
        )).scalar_one()
    await m.answer(f"Пользователей: {cnt}")

@router.message(StatsStates.waiting_choice, F.text == ("💳 Оплаты"))
async def stats_orders(m: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        paid = (await s.execute(
            select(func.count()).select_from(Order).where(Order.status == "paid")
        )).scalar_one()
    await m.answer(f"Оплаченных заказов: {paid}")

@router.message(StatsStates.waiting_choice, F.text == ("⬅️ Назад в меню"))
async def stats_back(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Вернулся в меню. /menu")
