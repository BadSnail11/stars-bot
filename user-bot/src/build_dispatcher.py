from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker
from .handlers import start, menu, stars, premium, history, referral  # какие нужны

def build_dispatcher(session_maker: async_sessionmaker) -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.get_router(session_maker))
    dp.include_router(menu.get_router(session_maker))
    dp.include_router(stars.get_router(session_maker))
    dp.include_router(premium.get_router(session_maker))
    dp.include_router(history.get_router(session_maker))
    dp.include_router(referral.get_router(session_maker))
    return dp
