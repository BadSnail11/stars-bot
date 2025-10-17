import os
import aiohttp
from typing import Optional, Literal, TypedDict

PAYMENT_API = os.getenv("PAYMENT_API_BASE", "http://payment-api:8081").rstrip("/")

PaymentMethod = Literal["TON", "SBP", "CRYPTO_OTHER"]
OrderType = Literal["stars", "premium", "ton"]

class CreateOrderResult(TypedDict, total=False):
    order_id: int
    status: str
    message: Optional[str]
    ton: dict
    sbp: dict
    other: dict
    # у HELEKET ответ может прийти текстом в message (или расширите API при желании)

async def create_order(
    *, user_tg_id: int, username: Optional[str],
    recipient: Optional[str],
    order_type: OrderType, amount: int,
    payment_method: PaymentMethod,
    bot_tg_id: int
) -> CreateOrderResult:
    body = {
        "user_tg_id": user_tg_id,
        "username": username,
        "recipient": recipient,
        "order_type": order_type,
        "amount": amount,
        "payment_method": payment_method,
        "bot_tg_id": bot_tg_id
    }
    async with aiohttp.ClientSession() as http:
        async with http.post(f"{PAYMENT_API}/orders", json=body, timeout=30) as r:
            r.raise_for_status()
            return await r.json()

async def get_order_status(order_id: int) -> dict:
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{PAYMENT_API}/orders/{order_id}", timeout=15) as r:
            r.raise_for_status()
            return await r.json()
