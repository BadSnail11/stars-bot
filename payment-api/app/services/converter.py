from ..models import Order
from ..repositories.pricing import PricingRepo
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.pricing import calc_ton_for_stars, calc_ton_for_premium
import requests

from currency_converter import CurrencyConverter

async def get_amount(session: AsyncSession, order: Order, bot_id: int) -> float | None:
    repo = PricingRepo(session)
    price_ton = await repo.get_active_dynamic(order.type, "TON", bot_id)
    if order.type == "stars":
        self_price = float(calc_ton_for_stars(order.amount, price_ton.manual_price))
    if order.type == "premium":
        self_price = float(calc_ton_for_premium(order.amount, price_ton.manual_price))

    price = order.price
    if order.currency == "TON":
        marge = price - self_price

        amount = marge / 100 * 40

        return await convert_ton_to_usd(amount)
    elif order.currency == "RUB":
        # price_rub = await repo.get_active_manual(order.type, "RUB", bot_id)

        # if order.type == "stars":
        #     self_price = calc_rub_for_stars(order.amount, price_rub.manual_price)
        # if order.type == "premium":
        #     self_price = calc_rub_for_premium(order.amount, price_rub.manual_price)
        self_price = float(await convert_ton_to_rub(self_price))

        marge = float(price) - self_price

        amount = marge / 100 * 40

        return await convert_rub_to_usd(amount)


        



async def get_ton_to_usd_price():
    """Получает текущую цену TON в USD через CoinGecko API"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'the-open-network',
            'vs_currencies': 'usd'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        ton_price = data['the-open-network']['usd']
        return ton_price
        
    except requests.exceptions.RequestException as e:
        return None

async def convert_ton_to_usd(amount) -> float| None:
    """Конвертирует количество TON в USD"""
    price = await get_ton_to_usd_price()
    if price is not None:
        usd_amount = amount * price
        return usd_amount
    else:
        return None

async def convert_ton_to_rub(amount: float) -> float:
    usd_amount = await convert_ton_to_usd(amount)
    c = CurrencyConverter()
    usd_to_rub = float(c.convert(1, 'RUB', 'USD'))
    return usd_amount / usd_to_rub

async def convert_rub_to_usd(amount: float) -> float:
    c = CurrencyConverter()
    return float(c.convert(amount, 'RUB', 'USD'))

async def convert_usd_to_ton(amount: float) -> float:
    one_ton = await convert_ton_to_usd(1)
    return amount / one_ton
