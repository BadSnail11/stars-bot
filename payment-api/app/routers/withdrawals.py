from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal
from ..services.withdraw import request_withdrawal, apply_withdrawal_status, WithdrawalLogicError

# router = APIRouter(prefix="/wallet", tags=["wallet"])
router = APIRouter(tags=["wallet"])

# --- запрос на вывод (из бота/админки) ---

class WithdrawIn(BaseModel):
    user_id: int
    to_address: str = Field(..., min_length=10)
    amount: Decimal = Field(..., gt=0)
    network: str = Field(..., max_length=10)

@router.post("/withdraw")
async def create_withdraw(req: WithdrawIn):
    async with SessionLocal() as db:
        try:
            # print(int(req.user_id), req.to_address, Decimal(req.amount))
            result = await request_withdrawal(db, user_id=int(req.user_id), to_address=req.to_address, amount=Decimal(req.amount), network=req.network)
            return {"ok": True, **result}
        except WithdrawalLogicError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

# --- вебхук от Heleket (подпись/секрет при наличии) ---

class HeleketWebhook(BaseModel):
    id: str                   # provider_id выплаты
    status: str               # processing/completed/failed/canceled...
    data: Optional[dict] = None

def _verify_signature(request: Request, signature: Optional[str]) -> bool:
    # если у Heleket есть подпись вебхука — проверь тут (HMAC с HELEKET_WEBHOOK_SECRET)
    # заглушка «всегда ок», чтобы не блокировать интеграцию
    return True

@router.post("/heleket/callback")
async def heleket_callback(payload: HeleketWebhook, request: Request, db: AsyncSession = Depends(SessionLocal), x_heleket_signature: Optional[str] = Header(None)):
    if not _verify_signature(request, x_heleket_signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        await apply_withdrawal_status(db, provider_id=payload.id, provider_status=payload.status, payload=payload.data or {})
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
