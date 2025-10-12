from aiogram import Router, types, F
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.db import SessionLocal
from src.utils.owner_scope import resolve_owner_and_bot_key

router = Router()

@router.message(CommandStart())
async def start(m: types.Message):
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
    if not bot_key:
        await m.answer("У вас нет привязанного зеркального бота. Сначала создайте его в пользовательском боте.")
    else:
        await m.answer("Добро пожаловать в админ-панель вашего бота.\nВыберите раздел в меню /menu")
