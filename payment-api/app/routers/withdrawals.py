from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.converter import convert_usd_to_ton

from ..db import SessionLocal
from ..services.withdraw import create_withdraw_request

router = APIRouter(tags=["wallet"])

class WithdrawIn(BaseModel):
    user_id: int
    to_address: str
    amount: float
    # network: str

@router.post("/withdraw")
async def create_withdraw(req: WithdrawIn):
    async with SessionLocal() as db:
        try:
            # print(int(req.user_id), req.to_address, Decimal(req.amount))
            # result = await request_withdrawal(db, user_id=int(req.user_id), to_address=req.to_address, amount=Decimal(str(req.amount)), network=req.network)
            ton_amount = await convert_usd_to_ton(float(req.amount))
            print(ton_amount)
            result = await create_withdraw_request(ton_amount, req.to_address)
            return {"ok": True, "tx": result}
        # except WithdrawalLogicError as e:
        #     raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


# @router.post("/heleket/callback")
# async def heleket_callback(payload: HeleketWebhook, request: Request, db: AsyncSession = Depends(SessionLocal), x_heleket_signature: Optional[str] = Header(None)):
#     if not _verify_signature(request, x_heleket_signature):
#         raise HTTPException(status_code=401, detail="invalid signature")

#     try:
#         await apply_withdrawal_status(db, provider_id=payload.id, provider_status=payload.status, payload=payload.data or {})
#         return {"ok": True}
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=str(e))
