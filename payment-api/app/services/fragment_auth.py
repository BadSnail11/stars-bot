import os, time, aiohttp
from typing import Dict, Any, Optional, List

_BASE = (os.getenv("FRAGMENT_BASE") or "https://api.fragment-api.com").rstrip("/")
_AUTH_PATH = os.getenv("FRAGMENT_EP_AUTH", "/v1/authenticate")
_AUTH_URL = _BASE + (_AUTH_PATH if _AUTH_PATH.startswith("/") else "/" + _AUTH_PATH)

_API_KEY = os.getenv("FRAGMENT_API_KEY", "").strip()
_PHONE = os.getenv("FRAGMENT_PHONE", "").strip()
_VERSION = os.getenv("FRAGMENT_VERSION", "W5").strip()

def _mnemonics() -> List[str]:
    raw = os.getenv("FRAGMENT_MNEMONICS", "")
    return [w.strip() for w in raw.replace(",", " ").split() if w.strip()]

def _check_mnemonics() -> List[str]:
    raw = os.getenv("FRAGMENT_CHECK_MNEMONICS", "")
    return [w.strip() for w in raw.replace(",", " ").split() if w.strip()]

class FragmentAuth:
    """Singleton-авторизация с кэшированием токена."""
    def __init__(self):
        self._token: Optional[str] = None
        self._check_token: Optional[str] = None
        self._exp_ts: float = 0

    def _is_valid(self) -> bool:
        return bool(self._token) and (time.time() + 30 < self._exp_ts)

    async def _fetch_token(self) -> None:
        if not _API_KEY or not _PHONE:
            raise RuntimeError("FRAGMENT_API_KEY или FRAGMENT_PHONE не заданы")

        # print(_mnemonics())
        payload = {
            "api_key": _API_KEY,
            "phone_number": _PHONE,
            "version": _VERSION,
            "mnemonics": _mnemonics(),
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as http:
            async with http.post(_AUTH_URL, json=payload) as r:
                try:
                    data = await r.json()
                except Exception:
                    r.raise_for_status()
                    raise
                if r.status >= 400:
                    raise RuntimeError(f"Authenticate failed {r.status}: {data}")

        token = data.get("token") or data.get("access_token")
        if not token:
            raise RuntimeError(f"Authenticate: токен не найден в ответе: {data}")

        now = time.time()
        self._exp_ts = now + float(data.get("expiresIn") or data.get("expires_in") or 3600)
        self._token = str(token)

    async def _fetch_check_token(self) -> None:
        if not _API_KEY or not _PHONE:
            raise RuntimeError("FRAGMENT_API_KEY или FRAGMENT_PHONE не заданы")

        # print(_mnemonics())
        payload = {
            "api_key": _API_KEY,
            "phone_number": _PHONE,
            "version": _VERSION,
            "mnemonics": _check_mnemonics(),
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as http:
            async with http.post(_AUTH_URL, json=payload) as r:
                try:
                    data = await r.json()
                except Exception:
                    r.raise_for_status()
                    raise
                if r.status >= 400:
                    raise RuntimeError(f"Authenticate failed {r.status}: {data}")

        token = data.get("token") or data.get("access_token")
        if not token:
            raise RuntimeError(f"Authenticate: токен не найден в ответе: {data}")

        now = time.time()
        self._exp_ts = now + float(data.get("expiresIn") or data.get("expires_in") or 3600)
        self._check_token = str(token)

    async def get_auth_header(self) -> Dict[str, str]:
        if not self._is_valid():
            await self._fetch_token()
        return {"Authorization": f"JWT {self._token}"}
    
    async def get_auth_check_header(self) -> Dict[str, str]:
        if not self._is_valid():
            await self._fetch_check_token()
        return {"Authorization": f"JWT {self._token}"}

auth = FragmentAuth()
