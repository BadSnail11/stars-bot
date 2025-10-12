from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from src.db import SessionLocal
from src.repositories.required_channels import RequiredChannelsRepo
from src.utils.owner_scope import resolve_owner_and_bot_key
from src.utils.mirror_bot import get_mirror_bot

router = Router(name="channels")

class ChannelsStates(StatesGroup):
    waiting_action = State()   # ждём @username или -@username

async def _render_list(m: types.Message, s, bot_key: int):
    rows = await RequiredChannelsRepo(s).list_active(bot_key)
    text = "Обязательные каналы:\n" + ("\n".join(f"• {r.channel_username}" for r in rows) or "— список пуст —")
    text += "\n\nОтправьте @username для добавления\nОтправьте -@username для отключения\n/cancel — в меню"
    await m.answer(text)

@router.message(F.text == ("🔗 Каналы"))
async def channels_enter(m: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден. Сначала создайте бота.")
            return
        await _render_list(m, s, bot_key)
    await state.set_state(ChannelsStates.waiting_action)

@router.message(ChannelsStates.waiting_action, F.text.startswith("-@"))
async def channels_remove(m: types.Message, state: FSMContext):
    ch = (m.text or "").strip()[1:]
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.")
            return
        await RequiredChannelsRepo(s).disable(bot_key, ch)
        await m.answer(f"Отключил канал {ch}.")
        await _render_list(m, s, bot_key)

@router.message(ChannelsStates.waiting_action, F.text.startswith("@"))
async def channels_add(m: types.Message, state: FSMContext):
    ch = (m.text or "").strip()
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.")
            return
        mirror = await get_mirror_bot(s, bot_key)
        if not mirror:
            await m.answer("Зеркальный бот не запущен. Перезапустите и повторите.")
            return
        try:
            me = await mirror.get_me()
            cm = await mirror.get_chat_member(ch, me.id)
            if str(getattr(cm, "status", "")) not in {"administrator", "creator"}:
                await m.answer("Добавьте вашего зеркального бота в администраторы канала.")
                await mirror.session.close()
                return
        except Exception:
            await m.answer("Не удалось проверить канал. Проверьте username и доступ.")
            if mirror: await mirror.session.close()
            return
        await RequiredChannelsRepo(s).add(bot_key, ch)
        await m.answer(f"Добавлен канал {ch}.")
        await _render_list(m, s, bot_key)
        await mirror.session.close()
