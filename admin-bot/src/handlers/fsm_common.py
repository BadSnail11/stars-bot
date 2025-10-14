from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router(name="fsm_common")

@router.message(Command("cancel"))
async def cancel_or_menu(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Главное меню:\n"
        "• 🔗 Каналы\n• 💲 Цены\n• 📣 Рассылка\n• 📊 Статистика",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🔗 Каналы"), types.KeyboardButton(text="💲 Цены")],
                [types.KeyboardButton(text="📣 Рассылка"), types.KeyboardButton(text="📊 Статистика")],
            ],
            resize_keyboard=True
        )
    )
