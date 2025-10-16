import os, aiohttp
from typing import Any, Dict
from .fragment_auth import auth

def _base() -> str:
    return (os.getenv("FRAGMENT_BASE") or "https://api.fragment-api.com").rstrip("/")

def _ep(name_env: str, default_path: str) -> str:
    path = os.getenv(name_env, default_path)
    if not path.startswith("/"):
        path = "/" + path
    return _base() + path

async def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = await auth.get_auth_header()
    headers["Content-Type"] = "application/json"
    async with aiohttp.ClientSession() as http:
        async with http.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
            try:
                data = await r.json()
            except Exception:
                r.raise_for_status()
                raise
            if r.status >= 400:
                raise RuntimeError(f"Fragment API error {r.status}: {data}")
            return data
        
async def _get(url: str):
    headers = await auth.get_auth_header()
    headers["Content-Type"] = "application/json"
    async with aiohttp.ClientSession() as http:
        async with http.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
            try:
                data = await r.json()
            except Exception:
                r.raise_for_status()
                raise
            if r.status >= 400:
                raise RuntimeError(f"Fragment API error {r.status}: {data}")
            return data
        
# async def _post_check_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
#     headers = await auth.get_auth_check_header()
#     headers["Content-Type"] = "application/json"
#     async with aiohttp.ClientSession() as http:
#         async with http.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
#             try:
#                 data = await r.json()
#             except Exception:
#                 r.raise_for_status()
#                 raise
#             return data

async def buy_stars(recipient: str, quantity: int) -> Dict[str, Any]:
    """Покупка / дарение звёзд"""
    url = _ep(f"FRAGMENT_EP_STARS/payment", "/v1/stars/payment")
    payload = {"query": recipient, "quantity": quantity, "show_sender": False}
    return await _post_json(url, payload)

async def buy_premium(recipient: str, months: int) -> Dict[str, Any]:
    """Покупка / дарение Premium"""
    url = _ep("FRAGMENT_EP_PREMIUM", "/v1/premium/buy")
    payload = {"query": recipient, "months": months, "show_sender": False}
    return await _post_json(url, payload)

# async def get_prices():
#     url = _ep("FRAGMENT_EP_STARS", "/v1/stars/buy")
#     # field = _recipient_field()
#     payload = {"username": "string", "quantity": 50, "show_sender": False}

async def get_stars_price() -> float:
    """Покупка / дарение Premium"""
    url = _ep("FRAGMENT_CHECK_STARS", "/v1/stars/price")
    # payload = {"query": recipient, "months": months, "show_sender": False}
    data = await _get(url)
    row = dict()
    for el in data:
        if el["stars"] == "50 stars":
            row = el
    amount = row["stars"].split(" ")[0]
    price = row["price_ton"]
    return price / amount

async def get_premium_price() -> float:
    """Покупка / дарение Premium"""
    url = _ep("FRAGMENT_CHECK_PREMIUM", "/v1/premium/price")
    # payload = {"query": recipient, "months": months, "show_sender": False}
    data = await _get(url)
    data = await _get(url)
    row = dict()
    for el in data:
        if el["duration"] == "3 months":
            row = el
    amount = row["months"].split(" ")[0]
    price = row["price_ton"]
    return price / amount