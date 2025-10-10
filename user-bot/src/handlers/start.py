from aiogram import Router, F, types
from aiogram.filters import CommandStart, CommandObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..repositories.users import UsersRepo
from ..repositories.channels import ChannelsRepo
from ..repositories.referrals import ReferralsRepo
from ..keyboards.common import offer_kb, check_subs_kb, main_menu_kb
from ..utils import get_env, is_subscribed

from ..repositories.referrals import ReferralsRepo
from ..services.subscription import check_user_subscriptions

from ..models import User

from sqlalchemy import select, insert, update


BTN_AGREE = "agree_offer"
BTN_DISAGREE = "disagree_offer"
BTN_CHECK_SUBS = "check_subs"

OFFER_URL = get_env("OFFER_URL", "https://example.com/offer")
OFFER_TEXT = f"Перед использованием подтвердите ознакомление с офертой.\n\n<a href='{OFFER_URL}'>Оферта</a>"

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="start")

    @router.message(CommandStart())
    async def default_cmd_start(m: types.Message, u: types.User | None = None, command: CommandObject | None = None):
        await cmd_start(m=m, u=u)

    @router.message(CommandStart(deep_link=True))
    async def cmd_start(m: types.Message, u: types.User | None = None, command: CommandObject | None = None):
        ref_code = command.args if command else None
        async with session_maker() as session:
            users = UsersRepo(session)
            # channels = ChannelsRepo(session)

            tg = u if u else m.from_user
            user = await users.upsert_from_telegram(tg)
            # user = await users.get_by_tg_id(tg.id)

            referrer_tg_id = int(ref_code) if (ref_code and ref_code.isdigit()) else None
            if referrer_tg_id:
                # найти referrer в users по tg_user_id
                ref_q = await session.execute(select(User).where(User.tg_user_id == referrer_tg_id))
                ref_user = ref_q.scalar_one_or_none()
                if ref_user:
                    refs = ReferralsRepo(session)
                    await refs.create_link_if_absent(ref_user.id, user.id)

            if not user.accepted_offer_at:
                print(user.accepted_offer_at)
                await m.answer(OFFER_TEXT, reply_markup=offer_kb(BTN_AGREE, BTN_DISAGREE))
                return

            # req_channels = await channels.get_active()
            # req_channels = req_channels or [get_env("REQUIRED_CHANNEL_FALLBACK", "@your_required_channel")]
            # missing = []
            # for ch in req_channels:
            #     if not await is_subscribed(m.bot, tg.id, ch):
            #         missing.append(ch)

            # if missing:
            #     await m.answer("Для использования бота подпишитесь на каналы:", reply_markup=check_subs_kb(missing, BTN_CHECK_SUBS))
            #     return

            ok, missing = await check_user_subscriptions(session, m.bot, m.from_user.id)

            if not ok:
                links = "\n".join(f"• {c}" for c in missing)
                await m.answer(
                    "Чтобы продолжить, подпишитесь на каналы:\n"
                    f"{links}\n\nПосле подписки нажмите «Проверить подписку».",
                    reply_markup=check_subs_kb(missing, BTN_CHECK_SUBS),  # кнопка повторной проверки
                )
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
        await cmd_start(cb.message, u=cb.from_user)

    return router
