from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router()

def admin_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔗 Каналы")
    kb.button(text="💲 Цены")
    kb.button(text="📣 Рассылка")
    kb.button(text="📊 Статистика")
    kb.adjust(2,2)
    return kb.as_markup(resize_keyboard=True)

@router.message(Command("menu"))
async def menu(m: types.Message):
    await m.answer("Выберите раздел:", reply_markup=admin_kb())
