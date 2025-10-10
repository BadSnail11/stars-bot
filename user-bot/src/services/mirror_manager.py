import asyncio
from typing import Dict, List
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from ..repositories.user_bots import UserBotsRepo, UserBot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select

class MirrorManager:
    """
    Держим пул задач dp.start_polling(bot) для всех «зеркал».
    Dispatcher один на всех; на каждое зеркало — свой Bot и задача.
    """
    def __init__(self, dp: Dispatcher, session_maker: async_sessionmaker[AsyncSession]):
        self.dp = dp
        self.session_maker = session_maker
        self._bots: Dict[int, Bot] = {}     # owner_user_id -> Bot
        self._tasks: Dict[int, asyncio.Task] = {}

    def is_running(self, owner_id: int) -> bool:
        t = self._tasks.get(owner_id)
        return bool(t and not t.done())

    async def bootstrap_existing(self) -> List[asyncio.Task]:
        """Поднять все активные зеркала при старте."""
        async with self.session_maker() as session:
            repo = UserBotsRepo(session)
            # выбери все is_active=True
            bots = await session.execute(
                select(UserBot).where(UserBot.is_active.is_(True))
            )  # если у тебя нет .__table__, просто сделай select(UserBot)...
            rows = bots.fetchall()

        tasks: List[asyncio.Task] = []
        for row in rows:
            owner_id = row.owner_user_id if hasattr(row, "owner_user_id") else row[0].owner_user_id
            token = row.tg_bot_token if hasattr(row, "tg_bot_token") else row[0].tg_bot_token
            if not self.is_running(owner_id):
                b = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                self._bots[owner_id] = b
                tasks.append(asyncio.create_task(self.dp.start_polling(b, handle_signals=False)))
        return tasks

    async def add_bot(self, owner_id: int, token: str) -> str:
        if self.is_running(owner_id):
            return "already_running"
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self._bots[owner_id] = bot
        task = asyncio.create_task(self.dp.start_polling(bot, handle_signals=False),
                                   name=f"mirror-bot-{owner_id}")
        self._tasks[owner_id] = task
        return "started"

    async def stop_bot(self, owner_id: int):
        t = self._tasks.get(owner_id)
        if t and not t.done():
            t.cancel()
        b = self._bots.pop(owner_id, None)
        if b:
            await b.session.close()
        self._tasks.pop(owner_id, None)
