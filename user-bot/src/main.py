import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .db import init_engine, close_engine, get_session_maker
from .handlers import start, menu, crypto, stars
from .utils import on_startup_banner

LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()

async def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.getenv("USER_BOT_TOKEN")
    if not token:
        raise RuntimeError("USER_BOT_TOKEN is not set")

    # DB
    await init_engine()
    session_maker = get_session_maker()

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # include routers
    dp.include_router(start.get_router(session_maker))
    dp.include_router(menu.get_router(session_maker))
    # dp.include_router(crypto.get_router(session_maker))
    dp.include_router(stars.get_router(session_maker))

    await on_startup_banner(bot)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await close_engine()

if __name__ == "__main__":
    asyncio.run(main())
