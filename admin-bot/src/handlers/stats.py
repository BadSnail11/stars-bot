# src/handlers/stats_excel.py
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, or_
from sqlalchemy.sql import nulls_last
from typing import List, Optional, Tuple
import io
from datetime import datetime, timedelta, timezone

from src.db import SessionLocal
from src.models import User, Order
from src.utils.owner_scope import resolve_owner_and_bot_key
from ..keyboards.common import nav_to_menu, stats_root_kb, periods_kb

# XLSX
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

router = Router(name="stats_excel")

# ----------------- FSM -----------------
class StatsStates(StatesGroup):
    idle = State()
    waiting_user_query = State()
    waiting_user_filter = State()
    waiting_period = State()            # общий шаг "выбор периода"
    waiting_period_user = State()       # выбор периода для заказов конкретного пользователя
    waiting_period_orders = State()     # выбор периода для всех заказов
    waiting_period_users = State()      # выбор периода для пользователей

# ----------------- Period Helpers -----------------
def _now_utc() -> datetime:
    # return datetime.now(timezone.utc)
    return datetime.utcnow()

def period_since(key: str) -> datetime:
    now = _now_utc()
    if key == "24h":
        return now - timedelta(hours=24)
    if key == "7d":
        return now - timedelta(days=7)
    if key == "30d":
        return now - timedelta(days=30)
    # fallback: 30d
    return now - timedelta(days=30)



# ----------------- Root -----------------

@router.callback_query(F.data == "stats")
async def stats_root(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(StatsStates.idle)
    await cb.message.edit_text("📊 Выберите, что экспортировать:", reply_markup=stats_root_kb())
    await cb.answer()

@router.callback_query(F.data == "statistics")
async def st_home(cb: types.CallbackQuery, state: FSMContext):
    await stats_root(cb, state)

# ----------------- XLSX utils -----------------
def _auto_width(ws):
    widths = {}
    for row in ws.rows:
        for cell in row:
            val = "" if cell.value is None else str(cell.value)
            widths[cell.column] = max(widths.get(cell.column, 0), len(val))
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(w + 2, 10), 60)

def _wb_from_table(sheet_title: str, headers: List[str], rows: List[Tuple]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31] or "Sheet1"
    ws.append(headers)
    for c in ws[1]:
        c.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append(list(r))
    _auto_width(ws)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

async def _bot_id_by_admin(s, admin_tg_id: int) -> Optional[int]:
    _, bot_id = await resolve_owner_and_bot_key(s, admin_tg_id)
    return bot_id

# ----------------- 1) Все заказы -----------------
def orders_filter_kb(scope: str, user_id: Optional[int] = None):
    uid = f"_{user_id}" if (scope == "user" and user_id is not None) else ""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Только успешные", callback_data=f"st_do_{scope}_paid{uid}"),
            types.InlineKeyboardButton(text="Все", callback_data=f"st_do_{scope}_all{uid}")
        ],
        [types.InlineKeyboardButton(text="⬅️ В разделы", callback_data="st_home")]
    ])

@router.callback_query(F.data == "st_orders")
async def st_orders(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(StatsStates.idle)
    await cb.message.edit_text("Экспорт заказов бота. Сначала выберите фильтр:", reply_markup=orders_filter_kb(scope="all"))
    await cb.answer()

# — выбрали paid/all → предлагаем период
@router.callback_query(F.data.in_(("st_do_all_paid", "st_do_all_all")))
async def st_orders_pick_period(cb: types.CallbackQuery, state: FSMContext):
    key = "st_do_all_paid" if cb.data.endswith("_paid") else "st_do_all_all"
    await cb.message.edit_text("Выберите период:", reply_markup=periods_kb(cbprefix=key))
    await cb.answer()

# — выбрали период → формируем XLSX
@router.callback_query(F.data.regexp(r"^st_do_all_(paid|all)_period_(24h|7d|30d)$"))
async def st_orders_do(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    print(cb.data.split("_"))
    _, _, _, mode, _, per = cb.data.split("_")  # all, paid|all, period, key
    only_paid = (mode == "paid")
    since = period_since(per)

    async with SessionLocal() as s:
        bot_id = await _bot_id_by_admin(s, m.chat.id)
        if not bot_id:
            await m.edit_text("Зеркальный бот не найден.", reply_markup=nav_to_menu()); await cb.answer(); return

        q = select(
            Order.id.label("order_id"),
            User.tg_user_id, User.username, User.first_name, User.last_name,
            Order.type, Order.amount, Order.price, Order.income, Order.currency,
            Order.status, Order.recipient, Order.created_at, Order.paid_at
        ).join(User, User.id == Order.user_id).where(User.bot_id == bot_id)

        if only_paid:
            q = q.where(Order.status == "paid", Order.paid_at >= since)
        else:
            q = q.where(Order.created_at >= since)

        q = q.order_by(
            Order.paid_at.desc().nullslast(),
            Order.created_at.desc()
        )
        rows = (await s.execute(q)).all()

    headers = ["OrderID","TG UserID","Username","First Name","Last Name",
               "Type","Amount","Price","Income","Currency","Status","Recipient",
               "CreatedAt","PaidAt"]
    data = []
    for r in rows:
        cr = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
        pr = r.paid_at.strftime("%Y-%m-%d %H:%M:%S") if r.paid_at else ""
        data.append((
            r.order_id, r.tg_user_id, r.username, r.first_name, r.last_name,
            r.type, r.amount, float(r.price or 0), float(r.income or 0), r.currency,
            r.status, r.recipient, cr, pr
        ))

    xbytes = _wb_from_table(
        sheet_title=f"orders_{mode}_{per}",
        headers=headers, rows=data
    )
    fname = f"orders_{mode}_{per}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    await m.bot.send_document(
        chat_id=m.chat.id,
        document=types.BufferedInputFile(xbytes, filename=fname),
        caption="Готово."
    )
    await cb.answer()

# ----------------- 2) Пользователи бота -----------------
@router.callback_query(F.data == "st_users")
async def st_users_pick_period(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Выберите период для экспорта пользователей:", reply_markup=periods_kb(cbprefix="st_do_users"))
    await cb.answer()

@router.callback_query(F.data.regexp(r"^st_do_users_period_(24h|7d|30d)$"))
async def st_users_do(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    per = cb.data.split("_")[-1]
    since = period_since(per)

    async with SessionLocal() as s:
        bot_id = await _bot_id_by_admin(s, m.chat.id)
        if not bot_id:
            await m.edit_text("Зеркальный бот не найден.", reply_markup=nav_to_menu()); await cb.answer(); return

        q = select(
            User.id, User.tg_user_id, User.username, User.first_name, User.last_name,
            User.lang_code, User.balance, User.accepted_offer_at, User.is_blocked, User.created_at
        ).where(User.bot_id == bot_id, User.created_at >= since).order_by(User.created_at.desc())
        rows = (await s.execute(q)).all()

    headers = ["ID","TG UserID","Username","First Name","Last Name","Lang",
               "Balance","AcceptedOfferAt","IsBlocked","CreatedAt"]
    data = []
    for r in rows:
        ao = r.accepted_offer_at.strftime("%Y-%m-%d %H:%M:%S") if r.accepted_offer_at else ""
        cr = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
        data.append((
            r.id, r.tg_user_id, r.username, r.first_name, r.last_name,
            r.lang_code, float(r.balance or 0), ao, bool(r.is_blocked), cr
        ))

    xbytes = _wb_from_table(f"users_{per}", headers, data)
    fname = f"users_{per}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    await m.bot.send_document(
        chat_id=m.chat.id,
        document=types.BufferedInputFile(xbytes, filename=fname),
        caption="Готово."
    )
    await cb.answer()

# ----------------- 3) Заказы конкретного пользователя -----------------
def ask_user_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ В разделы", callback_data="st_home")],
    ])

@router.callback_query(F.data == "st_user_orders")
async def st_user_orders(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    await state.set_state(StatsStates.waiting_user_query)
    await m.edit_text("Введите @username или числовой tg_user_id пользователя:", reply_markup=ask_user_kb())
    await cb.answer()

@router.message(StatsStates.waiting_user_query)
async def st_user_pick(m: types.Message, state: FSMContext):
    q = (m.text or "").strip()
    if not q:
        await m.answer("Пустой ввод. Повторите.", reply_markup=nav_to_menu()); return

    async with SessionLocal() as s:
        bot_id = await _bot_id_by_admin(s, m.chat.id)
        if not bot_id:
            await m.answer("Зеркальный бот не найден.", reply_markup=nav_to_menu()); return

        conds = []
        if q.startswith("@"):
            uname = q[1:].lower()
            conds.append(func.lower(User.username) == uname)
        elif q.isdigit():
            conds.append(User.tg_user_id == int(q))
        else:
            await m.answer("Ожидал @username или числовой tg_user_id.", reply_markup=nav_to_menu()); return

        res = await s.execute(
            select(User.id, User.username, User.tg_user_id)
            .where(User.bot_id == bot_id)
            .where(or_(*conds)).limit(1)
        )
        row = res.first()

    if not row:
        await m.answer("Пользователь не найден.", reply_markup=nav_to_menu()); return

    user_id, username, tg_user_id = row
    await state.update_data(bot_id=bot_id, user_id=user_id, username=(username or ""), tg=tg_user_id)

    # спрашиваем фильтр paid/all
    await m.answer(
        f"Пользователь: {('@' + username) if username else f'id{tg_user_id}'}\nВыберите фильтр:",
        reply_markup=orders_filter_kb(scope="user", user_id=user_id)
    )
    await state.set_state(StatsStates.waiting_user_filter)

# выбрали paid/all → спросить период
@router.callback_query(StatsStates.waiting_user_filter, F.data.regexp(r"^st_do_user_(paid|all)_(\d+)$"))
async def st_user_pick_period(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    mode, uid = parts[2], parts[3]
    await state.update_data(user_mode=mode, user_uid=int(uid))
    await cb.message.edit_text("Выберите период:", reply_markup=periods_kb(cbprefix=f"st_do_user_{mode}", extra=uid))
    await cb.answer()

# выбрали период → выгружаем XLSX
@router.callback_query(F.data.regexp(r"^st_do_user_(paid|all)_period_(24h|7d|30d)_(\d+)$"))
async def st_user_orders_do(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    _, _, _, mode, _, per, uid = cb.data.split("_")
    only_paid = (mode == "paid")
    user_id = int(uid)
    since = period_since(per)

    async with SessionLocal() as s:
        q = select(
            Order.id.label("order_id"),
            Order.type, Order.amount, Order.price, Order.income, Order.currency,
            Order.status, Order.recipient, Order.created_at, Order.paid_at
        ).where(Order.user_id == user_id)

        if only_paid:
            q = q.where(Order.status == "paid", Order.paid_at >= since)
        else:
            q = q.where(Order.created_at >= since)

        q = q.order_by(
            Order.paid_at.desc().nullslast(),
            Order.created_at.desc()
        )
        rows = (await s.execute(q)).all()

        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    headers = ["OrderID","Type","Amount","Price","Income","Currency",
               "Status","Recipient","CreatedAt","PaidAt"]
    data_rows = []
    for r in rows:
        cr = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
        pr = r.paid_at.strftime("%Y-%m-%d %H:%M:%S") if r.paid_at else ""
        data_rows.append((
            r.order_id, r.type, r.amount, float(r.price or 0),
            float(r.income or 0), r.currency, r.status, r.recipient, cr, pr
        ))

    uname = (f"@{u.username}" if (u and u.username) else f"id{u.tg_user_id if u else user_id}")
    xbytes = _wb_from_table(
        sheet_title=f"user_orders_{mode}_{per}",
        headers=headers, rows=data_rows
    )
    fname = f"user_orders_{uname.replace('@','')}_{mode}_{per}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    await m.bot.send_document(
        chat_id=m.chat.id,
        document=types.BufferedInputFile(xbytes, filename=fname),
        caption="Готово."
    )
    await state.clear()
    await cb.answer()
