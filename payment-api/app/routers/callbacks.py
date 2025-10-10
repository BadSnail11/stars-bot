# app/routers/callbacks.py
import json, base64, hashlib, os
from fastapi import APIRouter, Request, HTTPException
from ..db import SessionLocal
from ..repositories.orders import OrdersRepo
from ..services.referral_accrual import accrue_referral_reward
from ..services.fulfillment import fulfill_order

router = APIRouter(prefix="/callbacks", tags=["callbacks"])
HELEKET_PAYMENT_KEY = os.getenv("HELEKET_PAYMENT_API_KEY", "")

def _verify_heleket_signature(raw_body: bytes) -> dict:
    data = json.loads(raw_body.decode("utf-8"))
    sign = data.pop("sign", None)
    # Важно: хеш считается по ТОМУ ЖЕ JSON, который прислал Heleket (экранирование слешей уже учтено),
    # поэтому сериализуем с separators и ensure_ascii=True, а затем base64+md5.
    normalized = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    b64 = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
    calc = hashlib.md5((b64 + HELEKET_PAYMENT_KEY).encode("utf-8")).hexdigest()
    if not sign or calc != sign:
        raise HTTPException(400, "Invalid Heleket signature")
    return data

@router.post("/heleket")
async def heleket_webhook(request: Request):
    raw = await request.body()
    data = _verify_heleket_signature(raw)

    # ожидаемые поля: order_id, status, txid и т.д.
    order_id = data.get("order_id")
    status = (data.get("status") or "").lower()
    txid = data.get("txid")

    if not order_id:
        raise HTTPException(422, "order_id missing")

    # Нас интересует paid / paid_over
    if status in {"paid", "paid_over"}:
        async with SessionLocal() as session:
            orders = OrdersRepo(session)
            order = await orders.get_by_id(int(order_id)) if str(order_id).isdigit() else None
            # если ты используешь строковый order_id, то ищи по orders.gateway_payload->>'heleket_order_id'
            if not order:
                # fallback: найти по gateway_payload.order_id
                # ... твой поиск ...
                pass

            if order and order.status != "paid":
                await orders.mark_paid(order.id, txid or "n/a", income=None)
                fresh = await orders.get_by_id(order.id)
                await accrue_referral_reward(session, fresh)
                await fulfill_order(session, fresh)

    return {"ok": True}
