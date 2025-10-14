from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from ..repositories.user_bots import UserBotsRepo
from src.db import SessionLocal
import os

from ..keyboards.common import admin_kb

router = Router()


@router.message(Command("menu"))
async def menu(m: types.Message):
    async with SessionLocal() as s:
        tg_user_id = m.chat.id
        user_repo = UserBotsRepo(s)
        bot = await user_repo.get_by_owner_tg(tg_user_id)
        main_bot = os.getenv("MAIN_BOT", "")
        is_main = False
        if main_bot and bot.tg_bot_id == int(main_bot):
            is_main = True
        await m.answer("Выберите раздел:", reply_markup=admin_kb(is_super=bot.is_super, is_main=is_main))

@router.callback_query(F.data == "back")
async def menu(cb: types.CallbackQuery):
    m = cb.message
    async with SessionLocal() as s:
        tg_user_id = m.chat.id
        user_repo = UserBotsRepo(s)
        bot = await user_repo.get_by_owner_tg(tg_user_id)
        main_bot = os.getenv("MAIN_BOT", "")
        is_main = False
        if main_bot and bot.tg_bot_id == int(main_bot):
            is_main = True
        await m.edit_text("Выберите раздел:", reply_markup=admin_kb(is_super=bot.is_super, is_main=is_main))

@router.callback_query(F.data == "file_back")
async def menu(cb: types.CallbackQuery):
    m = cb.message
    async with SessionLocal() as s:
        tg_user_id = m.chat.id
        user_repo = UserBotsRepo(s)
        bot = await user_repo.get_by_owner_tg(tg_user_id)
        main_bot = os.getenv("MAIN_BOT", "")
        is_main = False
        if main_bot and bot.tg_bot_id == int(main_bot):
            is_main = True
        await m.answer("Выберите раздел:", reply_markup=admin_kb(is_super=bot.is_super, is_main=is_main))
