from aiogram import Router, types, F
# from aiogram.filters import Text, Regexp
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from src.db import SessionLocal
from src.repositories.pricing import PricingRepo
from src.utils.owner_scope import resolve_owner_and_bot_key

router = Router(name="pricing")

class PricingStates(StatesGroup):
    waiting_price = State()

PRICE_RE = r"^(stars|premium)\s+[A-Z]{3}\s+\d+(?:[.,]\d+)?$"

async def _render_prices(m: types.Message, s, bot_key: int):
    repo = PricingRepo(s)
    stars = await repo.get_active_manual("stars", "RUB", bot_key)
    prem  = await repo.get_active_manual("premium", "RUB", bot_key)
    await m.answer(
        "Текущие manual-цены (RUB):\n"
        f"• звезда: {stars.manual_price if stars else '—'}\n"
        f"• премиум/мес: {prem.manual_price if prem else '—'}\n\n"
        "Отправьте:\n"
        "<code>stars RUB 1.23</code>\n"
        "<code>premium RUB 359</code>\n"
        "/cancel — в меню",
        parse_mode="HTML"
    )

@router.message(F.text == ("💲 Цены"))
async def pricing_enter(m: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.")
            return
        await _render_prices(m, s, bot_key)
    await state.set_state(PricingStates.waiting_price)

@router.message(PricingStates.waiting_price, F.regexp(PRICE_RE))
async def pricing_set(m: types.Message, state: FSMContext):
    item, currency, price_s = (m.text or "").split()
    price = float(price_s.replace(",", "."))
    async with SessionLocal() as s:
        _, bot_key = await resolve_owner_and_bot_key(s, m.from_user.id)
        if not bot_key:
            await m.answer("Зеркальный бот не найден.")
            return
        await PricingRepo(s).upsert_manual(item.lower(), currency.upper(), price, bot_key)
        await m.answer("Сохранено.")
        await _render_prices(m, s, bot_key)
