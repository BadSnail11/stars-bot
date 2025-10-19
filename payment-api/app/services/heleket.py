# app/services/heleket.py
import os, json, base64, hashlib, aiohttp, asyncio
from typing import Optional, Tuple
from decimal import Decimal
from typing import Dict, Any

HELEKET_BASE = os.getenv("HELEKET_BASE", "https://api.heleket.com")
MERCHANT = os.getenv("HELEKET_MERCHANT_UUID", "")
PAYMENT_KEY = os.getenv("HELEKET_PAYMENT_API_KEY", "")
PAYOUT_KEY = os.getenv("HELEKET_PAYOUT_API_KEY", "")

def _sign_payload(payload_obj: dict, is_payout: bool = False) -> str:
    data = json.dumps(payload_obj)

    encoded_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')

    key = PAYOUT_KEY if is_payout else PAYMENT_KEY

    # Создаем подпись MD5
    sign = hashlib.md5(f"{encoded_data}{key}".encode('utf-8')).hexdigest()
    return sign

async def _post_json(path: str, payload: dict, is_payout: bool = False) -> dict:
    url = f"{HELEKET_BASE}{path}"
    headers = {
        "merchant": MERCHANT,
        "sign": _sign_payload(payload, is_payout),
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as http:
        async with http.post(url, headers=headers, json=payload, timeout=30) as r:
            text = await r.text()
            r.raise_for_status()
            return json.loads(text)

async def create_invoice(
    amount: str,
    currency: str,
    order_id: str,
    user_tg_id: str,
    *,
    to_currency: Optional[str] = None,
    network: Optional[str] = None,
    url_return: Optional[str] = None,
    url_success: Optional[str] = None,
    url_callback: Optional[str] = None,
    lifetime: Optional[int] = None,
) -> dict:
    """
    POST /v1/payment — создаём инвойс (возвращает uuid, url, address, payment_status и т.д.)
    Документация: https://doc.heleket.com/methods/payments/creating-invoice
    """
    gen_order_id = await generate_order_id(order_id, user_tg_id)
    payload = {
        "amount": str(amount),
        "currency": currency,         # напр. RUB (мы конвертим в to_currency)
        "order_id": gen_order_id,         # должен быть уникален
    }
    if to_currency: payload["to_currency"] = to_currency  # напр. "USDT"
    if network:     payload["network"] = network          # напр. "tron"
    if url_return:  payload["url_return"] = url_return
    if url_success: payload["url_success"] = url_success
    if url_callback:payload["url_callback"] = url_callback
    if lifetime:    payload["lifetime"] = lifetime

    # Можно дополнительно ограничить список доступных монет:
    payer_cur = os.getenv("HELEKET_PAYER_CURRENCY")
    payer_net = os.getenv("HELEKET_PAYER_NETWORK")
    if payer_cur:
        payload["currencies"] = [{"currency": payer_cur, **({"network": payer_net} if payer_net else {})}]

    return await _post_json("/v1/payment", payload)

async def get_payment_info(*, uuid: Optional[str] = None, order_id: Optional[str] = None, user_tg_id: Optional[str] = None) -> dict:
    """
    POST /v1/payment/info — информация/статус инвойса.
    Документация: https://doc.heleket.com/methods/payments/payment-information
    """
    if not (uuid or order_id):
        raise ValueError("uuid or order_id required")
    payload = {}
    if uuid: payload["uuid"] = uuid
    if order_id and user_tg_id: 
        gen_order_id = await generate_order_id(order_id, user_tg_id)
        payload["order_id"] = gen_order_id
    return await _post_json("/v1/payment/info", payload)

def is_paid_status(status: str) -> bool:
    # Статусы по докам: paid, paid_over — считаем как успешную оплату
    return (status or "").lower() in {"paid", "paid_over"}

async def wait_invoice_paid(order_id: str, user_tg_id, *, poll_interval: float = 10.0, timeout: float = 900.0) -> Optional[dict]:
    """
    Пуллинг статуса до paid/paid_over/исчерпания таймаута.
    Возвращает объект платежа (result) если оплачен, иначе None.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        info = await get_payment_info(order_id=order_id, user_tg_id=user_tg_id)
        # success response: {"state":0, "result": {..., "status": "..."}}
        if info.get("state") == 0:
            res = info.get("result") or {}
            st = (res.get("status") or res.get("payment_status") or "").lower()
            if is_paid_status(st):
                return res
            # финальные неуспешные можно обрывать: cancel/fail/system_fail
            if st in {"cancel", "fail", "system_fail"} or res.get("is_final") is True:
                await asyncio.sleep(poll_interval)
    return None


async def create_withdraw(order_id: str, to_address: str, amount: str, network: str) -> dict:
    """
    Создать выплату. Возвращает (provider_id, payload).
    """
    # body = {"amount": str(amount),
    #         "currency": "USDT",
    #         "order_id": str(order_id),
    #         "address": str(to_address),
    #         "is_subtract": False,
    #         "network": str(network),
    #         # "url_callback": "http://89.223.126.202:8081/heleket/callback",
    #     }
    body = {"amount": "5",
            "currency": "USDT",
            "order_id": "1234",
            "address": "UQC_ttJKgwVO2hrKQ93DjFmUWj4YlYBno9huWIr_V2XdJtm8",
            "is_subtract": "0",
            "network": "TON",
            # "url_callback": "http://89.223.126.202:8081/heleket/callback",
        }
    return await _post_json("/v1/payout", body, True)

async def generate_order_id(order_id: str, user_tg_id: str):
    return hashlib.md5(f"{order_id}{user_tg_id}".encode('utf-8')).hexdigest()