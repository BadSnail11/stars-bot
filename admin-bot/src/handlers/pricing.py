from aiogram import Router, types, F
# from aiogram.filters import Text, Regexp
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from src.db import SessionLocal
from src.repositories.pricing import PricingRepo
from src.utils.owner_scope import resolve_owner_and_bot_key

from ..keyboards.common import pricing_kb, nav_to_menu, product_kb, product_markup_kb

router = Router(name="pricing")

class PricingStates(StatesGroup):
    waiting_stars_price = State()
    waiting_premium_price = State()
    waiting_ton_price = State()
    waiting_stars_markup = State()
    waiting_premium_markup = State()
    waiting_ton_markup = State()

# PRICE_RE = r"^\d+(?:[.,]\d+)?$"
PRICE_RE = r"^\d+\.\d*$"

async def _render_prices(m: types.Message, s, bot_key: int, edit: bool = False):
    repo = PricingRepo(s)
    stars = await repo.get_active_manual("stars", "RUB", bot_key)
    prem  = await repo.get_active_manual("premium", "RUB", bot_key)
    ton = await repo.get_active_manual("ton", "RUB", bot_key)
    stars_m = await repo.get_active_dynamic("stars", "TON", bot_key)
    prem_m = await repo.get_active_dynamic("premium", "TON", bot_key)
    ton_m = await repo.get_active_dynamic("ton", "TON", bot_key)
    if edit:
        await m.edit_text(
            "Текущие manual-цены (RUB):\n"
            f"• звезда: {stars.manual_price if stars else '—'}\n"
            f"• премиум/мес: {prem.manual_price if prem else '—'}\n"
            f"• ТОН: {ton.manual_price if prem else '—'}\n\n"
            f"• звезда (наценка TON): {stars_m.markup_percent if stars else '—'}%\n"
            f"• премиум/мес (наценка TON): {prem_m.markup_percent if prem else '—'}%\n"
            f"• ТОН (наценка TON): {ton_m.markup_percent if prem else '—'}%\n\n",
            parse_mode="HTML",
            reply_markup=pricing_kb()
        )
    else:
        await m.answer(
            "Текущие manual-цены (RUB):\n"
            f"• звезда: {stars.manual_price if stars else '—'}\n"
            f"• премиум/мес: {prem.manual_price if prem else '—'}\n\n"
            f"• ТОН: {ton.manual_price if prem else '—'}\n\n"
            f"• звезда (наценка TON): {stars_m.markup_percent if stars else '—'}%\n"
            f"• премиум/мес (наценка TON): {prem_m.markup_percent if prem else '—'}%\n\n"
            f"• ТОН (наценка TON): {ton_m.markup_percent if prem else '—'}%\n\n",
            parse_mode="HTML",
            reply_markup=pricing_kb()
        )

@router.callback_query(F.data == ("pricing"))
async def pricing_main(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await _render_prices(m, s, bot_key, True)
    # await state.set_state(PricingStates.waiting_price)

@router.callback_query(F.data == ("change_pricing"))
async def pricing_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Выберите продукт для изменения цены:", reply_markup=product_kb())
    # await state.set_state(PricingStates.waiting_price)

@router.callback_query(F.data == ("change_stars_pricing"))
async def pricing_stars_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую цену для звезд:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_stars_price)

@router.callback_query(F.data == ("change_premium_pricing"))
async def pricing_enter(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую цену для премиума:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_premium_price)

@router.callback_query(F.data == ("change_ton_pricing"))
async def pricing_ton_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую цену для ТОН:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_ton_price)

@router.message(PricingStates.waiting_stars_price)
async def pricing_set_stars(m: types.Message, state: FSMContext):
    try:
        price = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        stars = await repo.get_active_manual("stars", "RUB", bot_key)
        if stars:
            await repo.change_manual("stars", "RUB", price, bot_key)
        else:
            await repo.upsert_manual("stars", "RUB", price, bot_key)
        # await m.edit_text("Сохранено.", reply_markup=nav_to_menu())
        await _render_prices(m, s, bot_key)
    await state.clear()

@router.message(PricingStates.waiting_premium_price)
async def pricing_set_premium(m: types.Message, state: FSMContext):
    try:
        price = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        stars = await repo.get_active_manual("premium", "RUB", bot_key)
        if stars:
            await repo.change_manual("premium", "RUB", price, bot_key)
        else:
            await repo.upsert_manual("premium", "RUB", price, bot_key)
        # await m.edit_text("Сохранено.", reply_markup=nav_to_menu())
        await _render_prices(m, s, bot_key)
    await state.clear()

@router.message(PricingStates.waiting_ton_price)
async def pricing_set_ton(m: types.Message, state: FSMContext):
    try:
        price = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        stars = await repo.get_active_manual("ton", "RUB", bot_key)
        if stars:
            await repo.change_manual("ton", "RUB", price, bot_key)
        else:
            await repo.upsert_manual("ton", "RUB", price, bot_key)
        # await m.edit_text("Сохранено.", reply_markup=nav_to_menu())
        await _render_prices(m, s, bot_key)
    await state.clear()

######################################

@router.callback_query(F.data == ("change_markup"))
async def markup_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Выберите продукт для изменения наценки (TON):", reply_markup=product_markup_kb())
    # await state.set_state(PricingStates.waiting_price)

@router.callback_query(F.data == ("change_stars_markup"))
async def markup_stars_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую наценку % для звезд:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_stars_markup)

@router.callback_query(F.data == ("change_premium_markup"))
async def markup_enter(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую наценку % для премиума:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_premium_markup)

@router.callback_query(F.data == ("change_ton_markup"))
async def markup_stars_change(cb: types.CallbackQuery, state: FSMContext):
    m = cb.message
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.edit_text("Зеркальный бот не найден.", reply_markup=)
        #     return
        await m.edit_text(text="Введите новую наценку % для ТОН:", reply_markup=nav_to_menu())
    await state.set_state(PricingStates.waiting_ton_markup)

@router.message(PricingStates.waiting_stars_markup)
async def markup_set_stars(m: types.Message, state: FSMContext):
    try:
        markup = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        await repo.set_active_markup("stars", "TON", bot_key, markup)
        await _render_prices(m, s, bot_key)
    await state.clear()

@router.message(PricingStates.waiting_premium_markup)
async def markup_set_premium(m: types.Message, state: FSMContext):
    try:
        markup = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        await repo.set_active_markup("premium", "TON", bot_key, markup)
        await _render_prices(m, s, bot_key)
    await state.clear()

@router.message(PricingStates.waiting_ton_markup)
async def markup_set_stars(m: types.Message, state: FSMContext):
    try:
        markup = float(m.text.replace(",", "."))
    except:
        m.edit_text("Неправильный ввод, попробуйте еще раз:", nav_to_menu())
    # price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.chat.id)
        # if not bot_key:
        #     await m.answer("Зеркальный бот не найден.")
        #     return
        repo = PricingRepo(s)
        await repo.set_active_markup("ton", "TON", bot_key, markup)
        await _render_prices(m, s, bot_key)
    await state.clear()