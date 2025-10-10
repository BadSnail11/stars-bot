import asyncio
from typing import Iterable, List
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def _start_one(dp: Dispatcher, token: str):
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot, handle_signals=False)

async def run_all(dp: Dispatcher, tokens: Iterable[str]) -> None:
    tasks: List[asyncio.Task] = []
    for token in tokens:
        tasks.append(asyncio.create_task(_start_one(dp, token)))
    await asyncio.gather(*tasks)
