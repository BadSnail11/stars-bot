from ..models import Order
from ..repositories.pricing import PricingRepo
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.pricing import calc_ton_for_stars, calc_ton_for_premium
import requests

from currency_converter import CurrencyConverter

async def get_amount(session: AsyncSession, order: Order, bot_id: int) -> float:
    repo = PricingRepo(session)
    price_ton = await repo.get_active_dynamic(order.type, "TON", bot_id)
        
    if order.type == "stars":
        self_price = calc_ton_for_stars(order.amount, price_ton.manual_price)
    if order.type == "premium":
        self_price = calc_ton_for_premium(order.amount, price_ton.manual_price)

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
        self_price = await convert_ton_to_rub(self_price)

        marge = price - self_price

        amount = marge / 100 * 40

        return await convert_rub_to_usd(amount)


        



def get_ton_to_usd_price():
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
        print(f"Ошибка при запросе к API: {e}")
        return None

def convert_ton_to_usd(amount):
    """Конвертирует количество TON в USD"""
    price = get_ton_to_usd_price()
    if price is not None:
        usd_amount = amount * price
        return usd_amount
    else:
        return None

async def convert_ton_to_rub(amount: float) -> float:
    usd_amount = await convert_ton_to_usd(amount)
    c = CurrencyConverter()
    return c.convert(usd_amount, 'USD', 'RUB')

async def convert_rub_to_usd(amount: float) -> float:
    c = CurrencyConverter()
    return c.convert(amount, 'RUB', 'USD')