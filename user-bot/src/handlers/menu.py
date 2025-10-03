from aiogram import Router, F, types
from sqlalchemy.ext.asyncio import async_sessionmaker
from ..keyboards.common import main_menu_kb
from ..utils import get_env

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="menu")

    @router.message(F.text == "📄 Оферта")
    async def offer_msg(m: types.Message):
        offer_url = get_env("OFFER_URL", "https://example.com/offer")
        await m.answer(f"Оферта: <a href='{offer_url}'>читать</a>")

    @router.message(F.text == "🆘 Поддержка")
    async def support_msg(m: types.Message):
        support = get_env("SUPPORT_USERNAME", "@your_support")
        await m.answer(f"Напишите в поддержку: {support}")

    # @router.message(F.text.in_(["⭐ Купить звёзды", "💎 Купить TON", "👑 Премиум", "🧾 История заказов", "👥 Реферальная программа", "🤖 Создать свой бот"]))
    # async def placeholders(m: types.Message):
    #     await m.answer("Этот раздел появится на следующем шаге разработки.", reply_markup=main_menu_kb())

    return router
