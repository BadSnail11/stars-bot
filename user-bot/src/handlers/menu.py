from aiogram import Router, F, types
from sqlalchemy.ext.asyncio import async_sessionmaker
from ..keyboards.common import main_menu_kb, back_nav_kb
from ..utils import get_env

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="menu")

    @router.callback_query(F.data == "offer")
    async def offer_msg(cb: types.CallbackQuery):
        offer_url = get_env("OFFER_URL", "https://example.com/offer")
        await cb.message.edit_text(f"Оферта: <a href='{offer_url}'>читать</a>", reply_markup=back_nav_kb())

    @router.callback_query(F.data == "support")
    async def support_msg(cb: types.CallbackQuery):
        support = get_env("SUPPORT_USERNAME", "@your_support")
        await cb.message.edit_text(f"Напишите в поддержку: {support}", reply_markup=back_nav_kb())

    @router.callback_query(F.data == "nav_back")
    async def nav_back(cb: types.CallbackQuery):
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())

    # @router.message(F.text.in_(["⭐ Купить звёзды", "💎 Купить TON", "👑 Премиум", "🧾 История заказов", "👥 Реферальная программа", "🤖 Создать свой бот"]))
    # async def placeholders(m: types.Message):
    #     await m.answer("Этот раздел появится на следующем шаге разработки.", reply_markup=main_menu_kb())

    return router
