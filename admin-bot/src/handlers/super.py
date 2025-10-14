from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from ..repositories.user_bots import UserBotsRepo
from src.db import SessionLocal
from aiogram.fsm.context import FSMContext
import os
from aiogram.fsm.state import State, StatesGroup

from ..keyboards.common import nav_to_menu, admin_kb

router = Router()

class SuperStates(StatesGroup):
    get_username = State()

@router.callback_query(F.data == "super")
async def set_super(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    await m.edit_text("Введите @username бота для назначения или снятия статуса \"супер\":", reply_markup=nav_to_menu())
    await state.set_state(SuperStates.get_username)

@router.message(SuperStates.get_username)
async def menu(m: types.Message, state: FSMContext):
    q = (m.text or "").strip()
    if not q:
        await m.answer("Пустой ввод. Повторите.", reply_markup=nav_to_menu()); return
    async with SessionLocal() as s:
        if q.startswith("@"):
            uname = q
            # conds.append(func.lower(User.username) == uname)
        else:
            await m.answer("Ожидал @username", reply_markup=nav_to_menu()); return
        ub = UserBotsRepo(s)
        try:
            status = await ub.switch_is_super(uname)
            await m.answer(f"Статус \"супер\" изменен на: {"включен" if status else "выключен"}", reply_markup=nav_to_menu())
        except:
            await m.answer("Такого бота не существует", reply_markup=nav_to_menu())
