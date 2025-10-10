import os, aiohttp, uuid, asyncio
from typing import Optional

BASE = os.getenv("PLATEGA_BASE", "https://app.platega.io").rstrip("/")
MID  = os.getenv("PLATEGA_MERCHANT_ID", "")
SEC  = os.getenv("PLATEGA_SECRET", "")
METHOD_SBP = int(os.getenv("PLATEGA_METHOD_SBP", "2"))  # СБП/QR
RET_URL = os.getenv("PLATEGA_RETURN_URL", "https://example.com/ok")
FAIL_URL = os.getenv("PLATEGA_FAILED_URL", "https://example.com/fail")
TIMEOUT_SEC = int(os.getenv("PLATEGA_TIMEOUT_SEC", "900"))
POLL_INTERVAL = int(os.getenv("PLATEGA_POLL_INTERVAL_SEC", "5"))

def _hdrs():
    return {
        "Content-Type": "application/json",
        "X-MerchantId": MID,
        "X-Secret": SEC,
    }

async def create_sbp_invoice(amount_rub: int, description: str, payload: str) -> tuple[str, str]:
    """
    Возвращает (transaction_id, redirect_url)
    """
    print(MID, SEC)
    tx_id = str(uuid.uuid4())
    body = {
        "paymentMethod": METHOD_SBP,  # 2 - СБП/QR
        "id": tx_id,
        "paymentDetails": {"amount": amount_rub, "currency": "RUB"},
        "description": description,
        "return": RET_URL,
        "failedUrl": FAIL_URL,
        "payload": payload,
    }
    url = f"{BASE}/transaction/process"
    async with aiohttp.ClientSession() as http:
        async with http.post(url, json=body, headers=_hdrs()) as r:
            r.raise_for_status()
            data = await r.json()
            # ожидаем в ответе redirect + статус PENDING
            return tx_id, data.get("redirect") or ""

async def wait_payment_confirmed(transaction_id: str) -> Optional[str]:
    """
    Пуллим статус до CONFIRMED. Возвращает псевдо tx_hash (transaction_id),
    чтобы положить его в gateway_payload.tx_hash.
    """
    url = f"{BASE}/transaction/{transaction_id}"
    elapsed = 0
    async with aiohttp.ClientSession() as http:
        while elapsed <= TIMEOUT_SEC:
            async with http.get(url, headers=_hdrs()) as r:
                r.raise_for_status()
                data = await r.json()
            status = (data.get("status") or "").upper()
            if status == "CONFIRMED":
                return transaction_id
            if status in ("CANCELED", "FAILED", "EXPIRED"):
                return None
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
    return None
