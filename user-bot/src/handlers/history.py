from aiogram import Router, F, types
# from aiogram.filters import Text
from sqlalchemy.ext.asyncio import async_sessionmaker
from datetime import datetime
from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..repositories.user_bots import UserBotsRepo
from ..keyboards.common import history_nav_kb, main_menu_kb, back_nav_kb

PAGE_SIZE = 10

def _fmt_order(o) -> str:
    # Дата
    dt = o.paid_at or o.created_at
    dt_str = dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt)

    # Что купили
    if o.type == "stars":
        what = f"{o.amount} ⭐"
    elif o.type == "premium":
        what = f"Premium {o.amount} мес."
    else:
        what = f"{o.type} x {o.amount}"

    # Получатель (если подарок)
    rec = f" → {o.recipient}" if o.recipient else ""

    # Цена и валюта (если есть)
    price = f" — {o.price} {o.currency}" if o.price is not None and o.currency else ""

    return f"#{o.id} • {dt_str} • {what}{rec}{price}"

def get_router(session_maker: async_sessionmaker) -> Router:
    router = Router(name="history")

    async def _render_page(m: types.Message, user_tg, page: int, edit: bool = False):
        page = max(1, page)
        offset = (page - 1) * PAGE_SIZE

        async with session_maker() as session:
            users = UsersRepo(session)
            orders = OrdersRepo(session)
            userbots = UserBotsRepo(session)

            bot = await userbots.get_by_tg_bot_id(m.bot.id)
            user = await users.upsert_from_telegram(user_tg, bot.id)
            total = await orders.count_paid_by_user(user.id)
            rows = await orders.list_paid_by_user(user.id, limit=PAGE_SIZE, offset=offset)

        if total == 0:
            text = "Пока нет оплаченных заказов."
            await m.edit_text(text, reply_markup=back_nav_kb())
            return

        lines = ["📦 <b>История заказов</b>", f"Всего: {total}", ""]
        lines += [_fmt_order(o) for o in rows]
        text = "\n".join(lines)

        has_prev = page > 1
        has_next = offset + len(rows) < total
        kb = history_nav_kb(page, has_prev, has_next)

        if edit:
            await m.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        else:
            await m.answer(text, reply_markup=kb, disable_web_page_preview=True)

    # Вход из меню
    @router.callback_query(F.data == ("history"))
    async def history_entry(cb: types.CallbackQuery):
        m = cb.message
        await _render_page(m, m.from_user, page=1, edit=False)

    # Пагинация
    @router.callback_query(F.data.startswith("hist:"))
    async def history_paginate(cb: types.CallbackQuery):
        _, payload = cb.data.split(":", 1)
        if payload == "stay":
            await cb.answer()
            return
        try:
            page = int(payload)
        except Exception:
            page = 1
        await _render_page(cb.message, cb.from_user, page=page, edit=True)
        await cb.answer()

    return router
