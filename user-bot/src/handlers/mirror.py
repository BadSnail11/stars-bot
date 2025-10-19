from aiogram import Router, types, F, Bot, Dispatcher
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
import re, asyncio

from ..repositories.users import UsersRepo
from ..repositories.user_bots import UserBotsRepo
from ..repositories.pricing import PricingRepo
from ..services.polling_manager import PollingManager

from ..keyboards.common import back_nav_kb

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import os


TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_\-]{35,}$")

MAIN_BOT = os.getenv("MAIN_BOT", "")

class MirrorStates(StatesGroup):
    waiting_token = State()

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="mirror")

    @router.callback_query(F.data == "create_bot")
    async def ask_token(cb: types.CallbackQuery, state: FSMContext):
        m = cb.message
        async with session_maker() as session:
            users = UsersRepo(session)
            userbots = UserBotsRepo(session)

            bot = await userbots.get_by_tg_bot_id(cb.bot.id)
            inst = await cb.bot.get_chat_member(m.chat.id, m.chat.id)
            user = inst.user
            me = await users.upsert_from_telegram(user, bot.id)

            bots = UserBotsRepo(session)
            existing = await bots.get_by_owner(me.id)

            if existing and existing.is_active:
                await m.answer(
                    "У вас уже есть активное зеркало:\n"
                    f"<b>@{existing.bot_username}</b>\n\n"
                    "Пока можно создать только одно зеркало.",
                    reply_markup=back_nav_kb()
                )
                return

        await state.set_state(MirrorStates.waiting_token)
        await m.edit_text(
            "Пришлите токен вашего бота (@BotFather). "
            "Формат вроде <code>1234567890:AA...ZZ</code>.\n"
            "⚠️ Не публикуйте его в открытых чатах.", reply_markup=back_nav_kb()
        )

    @router.message(MirrorStates.waiting_token)
    async def receive_token(m: types.Message, state: FSMContext, dp_for_new_bot: Dispatcher, polling_manager: PollingManager):
        token = (m.text or "").strip()
        if not TOKEN_RE.match(token):
            await m.answer("Похоже, это не токен. Проверьте и пришлите снова.", reply_markup=back_nav_kb())
            return

        # валидируем токен через getMe
        test_bot = Bot(token=token)
        try:
            me = await test_bot.get_me()
        except Exception as e:
            await m.answer(f"Не получилось подключиться: <code>{e}</code>", reply_markup=back_nav_kb())
            await test_bot.session.close()
            return

        bot_username = me.username or ""
        tg_bot_id = me.bot.id
        await test_bot.session.close()

        # сохраняем в БД и запускаем зеркало
        async with session_maker() as session:
            users = UsersRepo(session)
            userbots = UserBotsRepo(session)
            pricing = PricingRepo(session)

            bot = await userbots.get_by_tg_bot_id(m.bot.id)
            u = await users.upsert_from_telegram(m.from_user, bot.id)

            bots = UserBotsRepo(session)
            existing = await bots.get_by_owner(u.id)
            if existing and existing.is_active:
                await m.answer(
                    "У вас уже есть активное зеркало. Сейчас можно только одно.",
                    reply_markup=back_nav_kb()
                )
                await state.clear()
                return

            if existing and not existing.is_active:
                # на будущее: можно сделать «переактивацию» — сейчас просто создадим новый
                pass

            created = await bots.create(owner_user_id=u.id, token=token, username=bot_username, tg_bot_id=tg_bot_id)

            main_bot_key = (await userbots.get_by_tg_bot_id(int(MAIN_BOT))).id
            main_price_stars = (await pricing.get_active_manual("stars", "RUB", main_bot_key)).manual_price
            main_price_premium = (await pricing.get_active_manual("premium", "RUB", main_bot_key)).manual_price
            await pricing.upsert_manual("stars", "RUB", float(main_price_stars), main_bot_key)
            await pricing.upsert_manual("premium", "RUB", float(main_price_premium), main_bot_key)

        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) 
        
        polling_manager.start_bot_polling(dp=dp_for_new_bot, bot=bot, dp_for_new_bot=dp_for_new_bot, polling_manager=polling_manager)
        
        await m.answer(f"Готово! Зеркало @{bot_username} запущено.\n"
                       "Администрируйте своего бота в @stars_admin_frag_bot", reply_markup=back_nav_kb())


        # по желанию удалим исходное сообщение с токеном (без паники, если нельзя)
        # try:
        #     await m.delete()
        # except Exception:
        #     pass

        # await m.answer(txt)
        # await state.clear()

    return router
