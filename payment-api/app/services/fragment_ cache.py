import os
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..redis import get_redis

FR_BASE = os.getenv("FRAGMENT_API_URL", "https://fragment-api.com/api/v1")
FR_API_KEY = os.getenv("FRAGMENT_API_KEY")
FR_PHONE   = os.getenv("FRAGMENT_PHONE")
FR_VER     = os.getenv("FRAGMENT_VERSION", "W5")
FR_MNEMO   = [w.strip() for w in (os.getenv("FRAGMENT_MNEMONICS","").split(",") if os.getenv("FRAGMENT_MNEMONICS") else [])]

TTL_DAYS = int(os.getenv("FRAGMENT_TOKEN_TTL_DAYS", "365"))
TTL_SECONDS = TTL_DAYS * 24 * 60 * 60

REDIS_KEY = "fragment:auth_token"

class FragmentAuthError(Exception): ...

async def _request_new_token(session: aiohttp.ClientSession) -> str:
    payload = {
        "api_key": FR_API_KEY,
        "phone_number": FR_PHONE,
        "version": FR_VER,
        "mnemonics": FR_MNEMO,
    }
    url = f"{FR_BASE}/authenticate"
    async with session.post(url, json=payload, timeout=30) as r:
        data = await r.json(content_type=None)
        if r.status != 200:
            raise FragmentAuthError(f"Auth failed: {r.status} {data}")
        token = data.get("token") or data.get("access_token") or data.get("bearer")
        if not token:
            raise FragmentAuthError(f"Auth response without token: {data}")
        return token

async def get_fragment_bearer(session: aiohttp.ClientSession) -> str:
    """
    Возвращает Bearer токен из Redis, если есть.
    Если нет — запрашивает у Fragment, сохраняет в Redis с TTL и возвращает.
    """
    redis = await get_redis()
    token = await redis.get(REDIS_KEY)
    if token:
        return token

    token = await _request_new_token(session)
    # сохранить токен + TTL (ключ сам истечёт через 365 дней)
    # можно также хранить JSON (token, obtained_at), но тут достаточно самого токена + expire
    await redis.set(REDIS_KEY, token, ex=TTL_SECONDS)
    return token

async def invalidate_fragment_bearer():
    """Принудительно сбросить токен (на случай 401 от Fragment)."""
    redis = await get_redis()
    await redis.delete(REDIS_KEY)
