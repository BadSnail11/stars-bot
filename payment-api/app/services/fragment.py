import os, aiohttp
from typing import Any, Dict


def _base() -> str:
    return (os.getenv("FRAGMENT_BASE") or "https://api.fragment-api.com").rstrip("/")

def _ep(name_env: str, default_path: str) -> str:
    path = os.getenv(name_env, default_path)
    if not path.startswith("/"):
        path = "/" + path
    return _base() + path

async def get_auth_header() -> Dict[str, str]:
    key = os.getenv("FRAGMENT_API_KEY", "")
    return {"api-key": key}

async def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = await get_auth_header()
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
    headers = await get_auth_header()
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
    payload = {"query": str(recipient), "quantity": str(quantity), "show_sender": "0"}
    return await _post_json(url, payload)

async def buy_premium(recipient: str, months: int) -> Dict[str, Any]:
    """Покупка / дарение Premium"""
    url = _ep("FRAGMENT_EP_PREMIUM", "/v1/premium/buy")
    payload = {"query": str(recipient), "months": str(months), "show_sender": "0"}
    return await _post_json(url, payload)

async def buy_ton(recipient: str, amount: float) -> Dict[str, Any]:
    url = url = _ep("FRAGMENT_EP_TON", "/v1/ads/topup")
    payload = {"query": str(recipient), "amount": str(amount), "show_sender": "0"}
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
        if el["stars"] == "50 Stars":
            row = el
    amount = row["stars"].split(" ")[0]
    price = row["price_ton"]
    return float(price) / float(amount)

async def get_premium_price() -> float:
    """Покупка / дарение Premium"""
    url = _ep("FRAGMENT_CHECK_PREMIUM", "/v1/premium/price")
    # payload = {"query": recipient, "months": months, "show_sender": False}
    data = await _get(url)
    row = dict()
    for el in data:
        if el["duration"] == "3 months":
            row = el
    amount = row["duration"].split(" ")[0]
    price = row["price_ton"]
    return float(price) / float(amount)
