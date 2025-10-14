from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from src.db import SessionLocal
from src.repositories.required_channels import RequiredChannelsRepo
from src.utils.owner_scope import resolve_owner_and_bot_key
from src.utils.mirror_bot import get_mirror_bot

from ..keyboards.common import channels_kb, nav_to_menu, list_channels_kb

router = Router(name="channels")

class ChannelsStates(StatesGroup):
    add_channel = State()

async def _render_list(m: types.Message, s, bot_key: int):
    rows = await RequiredChannelsRepo(s).list_active(bot_key)
    text = "Обязательные каналы:\n" + ("\n".join(f"• {r.channel_username}" for r in rows) or "— список пуст —")
    text += "\n\nОтправьте @username для добавления\nОтправьте -@username для отключения\n/cancel — в меню"
    await m.edit_text(text, reply_markup=channels_kb())

@router.callback_query(F.data == ("channels"))
async def channels_list(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.edit_text("Зеркальный бот не найден. Сначала создайте бота.", reply_markup=nav_to_menu())
            return
        await _render_list(m, s, bot_key)

@router.callback_query(F.data == ("add_channel"))
async def channels_add(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.edit_text("Зеркальный бот не найден. Сначала создайте бота.", reply_markup=nav_to_menu())
            return
        await m.edit_text("Отправьте @username канала для добавления:", reply_markup=nav_to_menu())
    await state.set_state(ChannelsStates.add_channel)


@router.message(ChannelsStates.add_channel, F.text.startswith("@"))
async def channels_enter(m: types.Message, state: FSMContext):
    ch = (m.text or "").strip()
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.", reply_markup=nav_to_menu())
            return
        mirror = await get_mirror_bot(s, bot_key)
        if not mirror:
            await m.answer("Зеркальный бот не запущен. Перезапустите и повторите.", reply_markup=nav_to_menu())
            return
        try:
            me = await mirror.get_me()
            cm = await mirror.get_chat_member(ch, me.id)
            if str(getattr(cm, "status", "")) not in {"administrator", "creator"}:
                await m.answer("Добавьте вашего зеркального бота в администраторы канала.", reply_markup=nav_to_menu())
                await mirror.session.close()
                return
        except Exception:
            await m.answer("Не удалось проверить канал. Проверьте username и доступ (бот должен быть администратором канала).", reply_markup=nav_to_menu())
            if mirror: await mirror.session.close()
            return
        await RequiredChannelsRepo(s).add(bot_key, ch)
        await m.answer(f"Добавлен канал {ch}.", reply_markup=nav_to_menu())
        await _render_list(m, s, bot_key)
        await mirror.session.close()
        await state.clear()


@router.callback_query(F.data == ("delete_channel"))
async def channels_delete(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.edit_text("Зеркальный бот не найден. Сначала создайте бота.", reply_markup=nav_to_menu())
            return
        rows = await RequiredChannelsRepo(s).list_active(bot_key)
        await m.edit_text("Выберите бота для удаления:", reply_markup=list_channels_kb(rows))
    await state.set_state(ChannelsStates.add_channel)

@router.callback_query(F.data.split("_")[0] == "delete", F.data.split("_")[1] == "id")
async def channels_delete_id(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.edit_text("Зеркальный бот не найден. Сначала создайте бота.", reply_markup=nav_to_menu())
            return
        channel_id = int(cb.data.split("_")[2])
        await RequiredChannelsRepo(s).remove(channel_id)
        await m.edit_text("Бот удален.", reply_markup=nav_to_menu())
    await state.set_state(ChannelsStates.add_channel)