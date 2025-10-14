from typing import List, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.required_channels import RequiredChannelsRepo
from .bot_context import resolve_bot_key
from ..models import RequiredChannel

async def fetch_required_channels(session: AsyncSession, bot: Bot) -> List[str]:
    """
    Вернёт список usernames каналов (вида @channel) для текущего бота.
    """
    bot_key = await resolve_bot_key(session, bot)
    repo = RequiredChannelsRepo(session)
    rows = await repo.list_active_for_bot_key(bot_key)
    # channel_username хранится как '@channel' — оставим как есть
    return [r.channel_username for r in rows]

async def check_user_subscriptions(session: AsyncSession, bot: Bot, user_id: int) -> Tuple[bool, List[str]]:
    """
    Проверяет, подписан ли user_id на все required_channels для текущего бота.
    Возвращает (ok, not_joined_list).
    """
    # print(bot.id, user_id)
    channels = await fetch_required_channels(session, bot)
    not_joined: List[str] = []

    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            status = getattr(member, "status", None)
            # joined если не 'left' и не 'kicked'
            if str(status) in ("left", "kicked", "ChatMemberLeft", "ChatMemberBanned"):
                not_joined.append(ch)
        except TelegramBadRequest:
            # если канал приватный/неправильный — считаем как «не подписан»
            not_joined.append(ch)

    # print(not_joined)

    return (len(not_joined) == 0, not_joined)
