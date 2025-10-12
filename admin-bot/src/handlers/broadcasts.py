from aiogram import Router, types, F
# from aiogram.filters import Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from src.db import SessionLocal
from src.repositories.broadcasts import BroadcastsRepo
from src.utils.owner_scope import resolve_owner_and_bot_key
from src.utils.mirror_bot import get_mirror_bot

router = Router(name="broadcasts")

class BroadcastStates(StatesGroup):
    waiting_text = State()

@router.message(F.text == ("📣 Рассылка"))
async def b_enter(m: types.Message, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_text)
    await m.answer("Пришлите текст рассылки (без медиа). /cancel — отмена")

@router.message(BroadcastStates.waiting_text)
async def b_send(m: types.Message, state: FSMContext):
    text = (m.text or "").strip()
    if not text:
        await m.answer("Текст пустой, отправьте сообщение с текстом.")
        return
    async with SessionLocal() as s:
        owner_id, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.")
            return
        repo = BroadcastsRepo(s)
        bid = await repo.create(author_user_id=owner_id, bot_key=bot_key, text=text)
        audience = await repo.audience_tg_ids(bot_key)

        mirror = await get_mirror_bot(s, bot_key)
        if not mirror:
            await m.answer("Зеркальный бот не запущен.")
            return

        ok = fail = 0
        for uid in audience:
            try:
                await mirror.send_message(uid, text)
                ok += 1
            except Exception:
                fail += 1

        await repo.mark_sent(bid, partial=(fail > 0))
        await mirror.session.close()

    await m.answer(f"Готово. Успешно: {ok}, ошибок: {fail}.")
    await state.clear()
