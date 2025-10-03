from decimal import Decimal, ROUND_UP
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.pricing import PricingRepo

async def get_star_price_in_ton(session: AsyncSession) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_manual(item_type="stars", currency="TON")
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'stars' в TON (pricing_rules)")
    return Decimal(str(rule.manual_price))

def calc_ton_for_stars(qty: int, price_per_star_ton: Decimal) -> Decimal:
    total = price_per_star_ton * Decimal(qty)
    # округляем вверх до 9 знаков (нанотоны)
    return total.quantize(Decimal("0.000000001"), rounding=ROUND_UP)


async def get_star_price_in_rub(session: AsyncSession) -> Decimal:
    repo = PricingRepo(session)
    rule = await repo.get_active_manual(item_type="stars", currency="RUB")
    if not rule or rule.manual_price is None:
        raise RuntimeError("Не задана цена 'stars' в RUB (pricing_rules)")
    return Decimal(str(rule.manual_price))

def calc_rub_for_stars(qty: int, price_per_star_rub: Decimal) -> int:
    total = (price_per_star_rub * Decimal(qty)).quantize(Decimal("1"), rounding=ROUND_UP)
    return int(total)  # Platega ждёт целую сумму в рублях