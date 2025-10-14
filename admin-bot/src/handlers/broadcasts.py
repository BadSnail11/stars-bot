# src/handlers/broadcasts.py
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import io

from src.db import SessionLocal
from src.models import User
from src.utils.owner_scope import resolve_owner_and_bot_key
from src.utils.mirror_bot import get_mirror_bot
from ..keyboards.common import nav_to_menu, broadcasts_kb  # используем твой "назад в меню"

router = Router(name="broadcasts")

class BroadcastStates(StatesGroup):
    waiting_content = State()

@router.callback_query(F.data == "broadcasts")
async def broadcasts_home(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    await state.clear()
    await m.edit_text(
        "Отправим либо <b>текст</b>, либо <b>текст с одной фотографией</b>.\n"
        "Нажмите «Создать рассылку», затем пришлите сообщение.",
        reply_markup=broadcasts_kb(),
        parse_mode="HTML",
    )
    await cb.answer()

@router.callback_query(F.data == "broadcasts_create")
async def broadcasts_create(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.edit_text("Зеркальный бот не найден. Сначала создайте бота.", reply_markup=nav_to_menu())
            await cb.answer()
            return
    await state.set_state(BroadcastStates.waiting_content)
    await m.edit_text(
        "Пришлите сообщение для рассылки:\n"
        "• только текст\n"
        "• или текст с <b>одной</b> фотографией (фото + подпись)\n\n",
        reply_markup=nav_to_menu(),
        parse_mode="HTML",
    )
    await cb.answer()

@router.message(BroadcastStates.waiting_content)
async def broadcasts_send(m: types.Message, state: FSMContext):
    text = (m.text or m.caption or "").strip()
    has_photo = bool(m.photo)
    photos_count = len(m.photo) if m.photo else 0

    # валидация по ТЗ
    if not text and not has_photo:
        await m.answer("Нужно прислать текст, либо текст с одной фотографией.", reply_markup=nav_to_menu())
        return
    # print(photos_count)
    # if has_photo and photos_count != 1:
    #     await m.answer("Приложите ровно одну фотографию (или отправьте только текст).", reply_markup=nav_to_menu())
    #     return
    if has_photo and not text:
        await m.answer("К фото должна быть подпись (текст).", reply_markup=nav_to_menu())
        return

    # аудитория и зеркало-бот
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.", reply_markup=nav_to_menu())
            return

        recipients = (await s.execute(
            select(User.tg_user_id).where(User.bot_id == bot_key)
        )).scalars().all()

        mirror = await get_mirror_bot(s, bot_key)
        if not mirror:
            await m.answer("Зеркальный бот не запущен. Перезапустите и повторите.", reply_markup=nav_to_menu())
            return

    sent_ok = sent_fail = 0

    try:
        if has_photo:
            # берём единственное фото (самое большое превью)
            ph = m.photo[-1]
            file = await m.bot.get_file(ph.file_id)
            buf = io.BytesIO()
            await m.bot.download(file, destination=buf)
            raw = buf.getvalue()

            # рассылаем фото+подпись
            for uid in recipients:
                try:
                    inp = types.BufferedInputFile(raw, filename=f"{ph.file_unique_id}.jpg")
                    await mirror.send_photo(uid, inp, caption=text, caption_entities=m.caption_entities)
                    sent_ok += 1
                except Exception:
                    sent_fail += 1
        else:
            # только текст
            for uid in recipients:
                try:
                    await mirror.send_message(uid, text, entities=m.entities)
                    sent_ok += 1
                except Exception:
                    sent_fail += 1
    finally:
        await mirror.session.close()

    await m.answer(f"Готово. Отправлено: {sent_ok}, ошибок: {sent_fail}.", reply_markup=nav_to_menu())
    await state.clear()
