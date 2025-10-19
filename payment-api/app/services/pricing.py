from decimal import Decimal, ROUND_UP, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.pricing import PricingRepo
from ..repositories.user_bots import UserBotsRepo
from .fragment import get_premium_price, get_stars_price
from ..db import SessionLocal
import asyncio

async def get_star_price_in_ton(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    # rule = await repo.get_active_manual(item_type="stars", currency="TON", bot_id=bot_id)
    # await update_ton_price(repo=repo, bot_id=bot_id)
    rule = await repo.get_active_dynamic(item_type="stars", currency="TON", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'stars' в TON (pricing_rules)")
    price = rule.manual_price + (rule.manual_price / 100 * rule.markup_percent)
    return Decimal(str(price))

def calc_ton_for_stars(qty: int, price_per_star_ton: Decimal) -> Decimal:
    total = price_per_star_ton * Decimal(qty)
    # округляем вверх до 9 знаков (нанотоны)
    return total.quantize(Decimal("0.000000001"), rounding=ROUND_UP)


async def get_star_price_in_rub(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_manual(item_type="stars", currency="RUB", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'stars' в RUB (pricing_rules)")
    return Decimal(str(rule.manual_price))

def calc_rub_for_stars(qty: int, price_per_star_rub: Decimal) -> int:
    total = (price_per_star_rub * Decimal(qty)).quantize(Decimal("1"), rounding=ROUND_UP)
    return int(total)  # Platega ждёт целую сумму в рублях

async def get_premium_price_in_rub(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_manual(item_type="premium", currency="RUB", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'premium' в RUB (pricing_rules)")
    return Decimal(str(rule.manual_price))

async def get_premium_price_in_ton(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    # await update_ton_price(repo=repo, bot_id=bot_id)
    rule = await repo.get_active_dynamic(item_type="premium", currency="TON", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'premium' в TON (pricing_rules)")
    price = rule.manual_price + (rule.manual_price / 100 * rule.markup_percent)
    return Decimal(str(price))

def calc_rub_for_premium(months: int, price_per_month_rub: Decimal) -> int:
    total = (price_per_month_rub * Decimal(months)).quantize(Decimal("1"), rounding=ROUND_UP)
    return int(total)

def calc_ton_for_premium(months: int, price_per_month_ton: Decimal) -> Decimal:
    total = price_per_month_ton * Decimal(months)
    return total.quantize(Decimal("0.000000001"), rounding=ROUND_UP)

async def get_ton_price_in_ton(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_dynamic(item_type="ton", currency="TON", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'ton' в TON (pricing_rules)")
    price = rule.manual_price + (rule.manual_price / 100 * rule.markup_percent)
    return Decimal(str(price))

def calc_ton_for_ton(amount: float, price_per_ton: Decimal) -> Decimal:
    total = price_per_ton * Decimal(amount)
    # округляем вверх до 9 знаков (нанотоны)
    return total.quantize(Decimal("0.000000001"), rounding=ROUND_UP)

async def get_ton_price_in_rub(session: AsyncSession, bot_id: int) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_manual(item_type="ton", currency="RUB", bot_id=bot_id)
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'ton' в RUB (pricing_rules)")
    # price = rule.manual_price + (rule.manual_price / 100 * rule.markup_percent)
    return Decimal(str(rule.manual_price))

def calc_rub_for_ton(amount: float, price_per_ton: Decimal):
    total = (price_per_ton * Decimal(amount)).quantize(Decimal("1"), rounding=ROUND_UP)
    return int(total)  # Platega ждёт целую сумму в рублях


async def update_ton_price():
    stars_price, premium_price = await get_stars_price(), await get_premium_price()
    async with SessionLocal() as session:
        repo = PricingRepo(session)
        user_bots = UserBotsRepo(session)
        bots = await user_bots.get_all()
        for bot in bots:
            await repo.set_active("stars", "TON", stars_price, bot.id)
            await repo.set_active("premium", "TON", premium_price, bot.id)
            await repo.set_active("ton", "TON", 1.0, bot.id)
    print("prices updated")
    await asyncio.sleep(60 * 10)


