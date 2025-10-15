import os, asyncio, aiohttp
from typing import Optional, Tuple
from decimal import Decimal
import hashlib


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def _get_provider():
    provider = (_env("TON_API_PROVIDER", "toncenter") or "toncenter").strip().lower()
    return "toncenter" if provider not in ("toncenter", "tonapi") else provider


async def _fetch_json(session: aiohttp.ClientSession, url: str, headers=None, params=None):
    async with session.get(url, headers=headers or {}, params=params or {}) as r:
        r.raise_for_status()
        return await r.json()


def _parse_ton_tx_amount(value) -> Decimal:
    try:
        nano = Decimal(str(value))
        return (nano / Decimal("1000000000")).quantize(Decimal("0.000000001"))
    except Exception:
        return Decimal("0")


def _extract_toncenter_incoming(tx: dict) -> Tuple[Optional[str], Decimal, Optional[str]]:
    tx_hash = tx.get("transaction_id", {}).get("hash") or tx.get("hash")
    in_msg = tx.get("in_msg") or tx.get("in_message") or {}
    msg_text = in_msg.get("message") or (in_msg.get("decoded_body") or {}).get("comment")
    amount = _parse_ton_tx_amount(in_msg.get("value", "0"))
    return tx_hash, amount, msg_text


def _extract_tonapi_incoming(tx: dict) -> Tuple[Optional[str], Decimal, Optional[str]]:
    tx_hash = tx.get("hash") or tx.get("transaction_id", {}).get("hash")
    in_msg = tx.get("in_msg") or tx.get("in_message") or tx.get("in_msg_decoded") or {}
    msg_text = in_msg.get("message") or (in_msg.get("decoded_body") or {}).get("comment")
    amount = _parse_ton_tx_amount(in_msg.get("value", "0"))
    return tx_hash, amount, msg_text


async def wait_ton_payment(wallet: str, memo: str, min_amount_ton: Decimal) -> Optional[str]:
    """
    Ждём входящую транзакцию TON:
    - на адрес `wallet`
    - с комментарием (memo) == ожидаемому токену
    - сумма >= min_amount_ton
    Возвращает tx_hash или None по таймауту.
    """
    base = (_env("TON_API_BASE") or "").strip().rstrip("/")
    api_key = (_env("TON_API_KEY") or "").strip()
    provider = _get_provider()
    timeout_sec = int(_env("TON_CONFIRM_TIMEOUT_SEC", "900"))
    interval = int(_env("TON_POLL_INTERVAL_SEC", "10"))

    if not base:
        base = "https://toncenter.com/api/v2" if provider == "toncenter" else "https://tonapi.io/v2"

    headers = {}
    if provider == "toncenter" and api_key:
        headers["X-API-Key"] = api_key
    if provider == "tonapi" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as http:
        elapsed = 0
        while elapsed <= timeout_sec:
            try:
                if provider == "toncenter":
                    url = f"{base}/getTransactions"
                    data = await _fetch_json(http, url, headers, params={"address": wallet, "limit": 50})
                    txs = data.get("result") or data.get("transactions") or []
                    for tx in txs:
                        tx_hash, amount, msg_text = _extract_toncenter_incoming(tx)
                        if msg_text and msg_text.strip() == memo and amount >= min_amount_ton:
                            return tx_hash
                else:
                    url = f"{base}/blockchain/getTransactions"
                    data = await _fetch_json(http, url, headers, params={"account": wallet, "limit": 50})
                    txs = data.get("transactions") or data.get("result") or []
                    for tx in txs:
                        tx_hash, amount, msg_text = _extract_tonapi_incoming(tx)
                        if msg_text and msg_text.strip() == memo and amount >= min_amount_ton:
                            return tx_hash
            except Exception:
                pass

            await asyncio.sleep(interval)
            elapsed += interval
    return None

async def generate_memo(preffix: str, order_id: str, user_tg_id: str):
    return hashlib.md5(f"{preffix}{order_id}{user_tg_id}".encode('utf-8')).hexdigest()
