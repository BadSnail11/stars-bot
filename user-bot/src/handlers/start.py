from aiogram import Router, F, types
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..repositories.users import UsersRepo
from ..repositories.channels import ChannelsRepo
from ..keyboards.common import offer_kb, check_subs_kb, main_menu_kb
from ..utils import get_env, is_subscribed

BTN_AGREE = "agree_offer"
BTN_DISAGREE = "disagree_offer"
BTN_CHECK_SUBS = "check_subs"

OFFER_URL = get_env("OFFER_URL", "https://example.com/offer")
OFFER_TEXT = f"Перед использованием подтвердите ознакомление с офертой.\n\n<a href='{OFFER_URL}'>Оферта</a>"

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="start")

    @router.message(CommandStart())
    async def cmd_start(m: types.Message, u: types.User | None = None):
        async with session_maker() as session:
            users = UsersRepo(session)
            channels = ChannelsRepo(session)

            tg = u if u else m.from_user
            user = await users.upsert_from_telegram(tg)
            # user = await users.get_by_tg_id(tg.id)

            if not user.accepted_offer_at:
                print(user.accepted_offer_at)
                await m.answer(OFFER_TEXT, reply_markup=offer_kb(BTN_AGREE, BTN_DISAGREE))
                return

            req_channels = await channels.get_active()
            req_channels = req_channels or [get_env("REQUIRED_CHANNEL_FALLBACK", "@your_required_channel")]
            missing = []
            for ch in req_channels:
                if not await is_subscribed(m.bot, tg.id, ch):
                    missing.append(ch)

            if missing:
                await m.answer("Для использования бота подпишитесь на каналы:", reply_markup=check_subs_kb(missing, BTN_CHECK_SUBS))
                return

            await m.answer("Добро пожаловать! Выберите действие:", reply_markup=main_menu_kb())

    @router.callback_query(F.data == BTN_AGREE)
    async def agree_offer(cb: types.CallbackQuery):
        async with session_maker() as session:
            users = UsersRepo(session)
            await users.set_offer_accepted_now(cb.from_user.id)
        await cb.message.edit_text("Спасибо! Оферта принята ✅\nПроверяю подписку…")
        await cmd_start(cb.message, cb.from_user)

    @router.callback_query(F.data == BTN_DISAGREE)
    async def disagree_offer(cb: types.CallbackQuery):
        await cb.message.edit_text("Вы можете вернуться к использованию бота после принятия оферты.")

    @router.callback_query(F.data == BTN_CHECK_SUBS)
    async def check_subs(cb: types.CallbackQuery):
        await cmd_start(cb.message, cb.from_user)

    return router
