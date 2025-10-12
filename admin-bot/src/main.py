import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
# from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder

# from .db import init_engine, close_engine, get_session_maker
from .handlers import start, menu, broadcasts, channels, pricing, stats, fsm_common
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.repositories.user_bots import UserBot

from aiogram.fsm.storage.memory import SimpleEventIsolation

LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()

async def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.getenv("ADMIN_BOT_TOKEN")
    if not token:
        raise RuntimeError("USER_BOT_TOKEN is not set")

    # DB
    # await init_engine()
    # session_maker = get_session_maker()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp = Dispatcher(events_isolation=SimpleEventIsolation())


    # # redis = Redis.from_url(os.getenv("REDIS_DSN", "redis://redis:6379/0"))
    # # storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_bot_id=True))

    # dp = build_dispatcher(session_maker=session_maker, redis_dsn=os.getenv("REDIS_DSN", "redis://redis:6379/0"))

    # await run_all(dp, tokens)

    # # bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp.include_router(fsm_common.router) 
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(pricing.router)
    dp.include_router(channels.router)
    dp.include_router(broadcasts.router)
    dp.include_router(stats.router)

    await dp.start_polling(bot)

    # poll = PollingManager(dp=dp, session_maker=session_maker)

    # # mirrors = MirrorManager(dp=dp, session_maker=session_maker)
    # dp.include_router(mirror.get_router(session_maker, poll))

    # tasks = [asyncio.create_task(poll.start_bot(owner_id=0, token=token))]

    # # Поднять ранее сохранённые пользовательские боты (если есть)
    # tasks += await poll.bootstrap_user_bots()

    # await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
