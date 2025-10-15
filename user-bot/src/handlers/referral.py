# src/handlers/referral.py
from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..services.referral import build_ref_link
from ..keyboards.common import main_menu_kb  # если у тебя есть главное меню

from sqlalchemy.ext.asyncio import async_sessionmaker

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="referral")

    @router.callback_query(F.data == "referal")
    async def show_ref_link(cb: types.CallbackQuery):
        m = cb.message
        me = await m.bot.get_me()
        link = build_ref_link(me.username or "", m.from_user.id)

        kb = InlineKeyboardBuilder()
        kb.button(text="🔗 Открыть ссылку", url=link)
        kb.button(text="⬅️ В меню", callback_data="back_to_menu")
        markup = kb.as_markup()

        text = (
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей по вашей ссылке и получайте 40% прибыли от их оплат.\n\n"
            f"Ваша ссылка:\n<code>{link}</code>"
        )
        await m.edit_text(text, reply_markup=markup)

    # опционально: обработчик «назад в меню»
    @router.callback_query(lambda c: c.data == "back_to_menu")
    async def back_to_menu(cb: types.CallbackQuery):
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
        await cb.answer()

    return router
