# src/core/dispatcher.py
from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.handlers import start, menu, stars, premium, history, referral, mirror

def build_dispatcher(session_maker: async_sessionmaker, redis_dsn: str) -> Dispatcher:
    # FSM-хранилище с ключами per-bot (как в мультибот-примере это обязательно)
    redis = Redis.from_url(redis_dsn)
    storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_bot_id=True))
    dp = Dispatcher(storage=storage)

    # Общие роутеры (одни и те же для всех ботов)
    dp.include_router(start.get_router(session_maker))
    dp.include_router(menu.get_router(session_maker))
    dp.include_router(stars.get_router(session_maker))
    dp.include_router(premium.get_router(session_maker))
    dp.include_router(history.get_router(session_maker))
    dp.include_router(referral.get_router(session_maker))
    dp.include_router(mirror.get_router(session_maker))  # кнопка «Создать свой бот» (см. шаг 4)

    return dp
