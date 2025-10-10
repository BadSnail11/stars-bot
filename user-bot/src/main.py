import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder

from src.services.mirror_manager import MirrorManager
from .db import init_engine, close_engine, get_session_maker
# from .build_dispatcher import build_dispatcher
from .utils import on_startup_banner
from src.handlers import mirror
from .handlers import start, menu, stars, premium, history, referral
from .services.mirror_manager import MirrorManager
from src.services.polling_manager import PollingManager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.core.dispatcher import build_dispatcher
from src.core.multibot import run_all
from src.repositories.user_bots import UserBot

from aiogram.fsm.storage.memory import SimpleEventIsolation

LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()

async def _load_tokens(session_maker: async_sessionmaker) -> list[str]:
    """
    Подгружаем ВСЕ токены: основной + активные зеркала из БД.
    Ровно как в примере: список токенов -> затем run_all(dp, tokens).
    """
    tokens: list[str] = []
    main_token = os.getenv("USER_BOT_TOKEN", "").strip()
    if not main_token:
        raise RuntimeError("USER_BOT_TOKEN не задан")

    tokens.append(main_token)

    async with session_maker() as session:
        rows = (await session.execute(
            select(UserBot.tg_bot_token).where(UserBot.is_active.is_(True))
        )).scalars().all()
        tokens.extend(t for t in rows if t and t != main_token)

    # Уберём дубли на всякий:
    seen, uniq = set(), []
    for t in tokens:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq

async def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # token = os.getenv("USER_BOT_TOKEN")
    # if not token:
    #     raise RuntimeError("USER_BOT_TOKEN is not set")

    # DB
    await init_engine()
    session_maker = get_session_maker()

    tokens = await _load_tokens(session_maker)

    bots = [Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) for token in tokens]

    dp = Dispatcher(session_maker=session_maker, events_isolation=SimpleEventIsolation())


    # # redis = Redis.from_url(os.getenv("REDIS_DSN", "redis://redis:6379/0"))
    # # storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_bot_id=True))

    # dp = build_dispatcher(session_maker=session_maker, redis_dsn=os.getenv("REDIS_DSN", "redis://redis:6379/0"))

    # await run_all(dp, tokens)

    # # bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # dp = Dispatcher(storage=storage)

    dp.include_router(start.get_router(session_maker))
    dp.include_router(menu.get_router(session_maker))
    dp.include_router(stars.get_router(session_maker))
    dp.include_router(premium.get_router(session_maker))
    dp.include_router(history.get_router(session_maker))
    dp.include_router(referral.get_router(session_maker))
    dp.include_router(mirror.get_router(session_maker))

    polling_manager = PollingManager()

    for bot in bots:
        await bot.get_updates(offset=-1)
    await dp.start_polling(*bots, dp_for_new_bot=dp, polling_manager=polling_manager)

    # poll = PollingManager(dp=dp, session_maker=session_maker)

    # # mirrors = MirrorManager(dp=dp, session_maker=session_maker)
    # dp.include_router(mirror.get_router(session_maker, poll))

    # tasks = [asyncio.create_task(poll.start_bot(owner_id=0, token=token))]

    # # Поднять ранее сохранённые пользовательские боты (если есть)
    # tasks += await poll.bootstrap_user_bots()

    # await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
