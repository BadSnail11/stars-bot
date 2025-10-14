# app/services/heleket.py
import os, json, base64, hashlib, aiohttp, asyncio
from typing import Optional, Tuple

HELEKET_BASE = os.getenv("HELEKET_BASE", "https://api.heleket.com")
MERCHANT = os.getenv("HELEKET_MERCHANT_UUID", "")
PAYMENT_KEY = os.getenv("HELEKET_PAYMENT_API_KEY", "")

def _sign_payload(payload_obj: dict) -> str:
    # md5(base64(json) + API_KEY)
    # raw = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
    # b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    # return hashlib.md5((b64 + PAYMENT_KEY).encode("utf-8")).hexdigest()
    data = json.dumps(payload_obj)  # или json.dumps(data, ensure_ascii=False) для кириллицы

    # PHP: $sign = md5(base64_encode($data) . $API_KEY);
    # Кодируем данные в base64
    encoded_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')

    # Создаем подпись MD5
    sign = hashlib.md5(f"{encoded_data}{PAYMENT_KEY}".encode('utf-8')).hexdigest()
    return sign

async def _post_json(path: str, payload: dict) -> dict:
    url = f"{HELEKET_BASE}{path}"
    headers = {
        "merchant": MERCHANT,
        "sign": _sign_payload(payload),
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
    payload = {
        "amount": str(amount),
        "currency": currency,         # напр. RUB (мы конвертим в to_currency)
        "order_id": order_id,         # должен быть уникален
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

async def get_payment_info(*, uuid: Optional[str] = None, order_id: Optional[str] = None) -> dict:
    """
    POST /v1/payment/info — информация/статус инвойса.
    Документация: https://doc.heleket.com/methods/payments/payment-information
    """
    if not (uuid or order_id):
        raise ValueError("uuid or order_id required")
    payload = {}
    if uuid: payload["uuid"] = uuid
    if order_id: payload["order_id"] = order_id
    return await _post_json("/v1/payment/info", payload)

def is_paid_status(status: str) -> bool:
    # Статусы по докам: paid, paid_over — считаем как успешную оплату
    return (status or "").lower() in {"paid", "paid_over"}

async def wait_invoice_paid(order_id: str, *, poll_interval: float = 5.0, timeout: float = 900.0) -> Optional[dict]:
    """
    Пуллинг статуса до paid/paid_over/исчерпания таймаута.
    Возвращает объект платежа (result) если оплачен, иначе None.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        info = await get_payment_info(order_id=order_id)
        # success response: {"state":0, "result": {..., "status": "..."}}
        if info.get("state") == 0:
            res = info.get("result") or {}
            st = (res.get("status") or res.get("payment_status") or "").lower()
            if is_paid_status(st):
                return res
            # финальные неуспешные можно обрывать: cancel/fail/system_fail
            print(st)
            if st in {"cancel", "fail", "system_fail"} or res.get("is_final") is True:
        await asyncio.sleep(poll_interval)
    return None
