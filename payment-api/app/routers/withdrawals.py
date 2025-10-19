from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.converter import convert_usd_to_ton
import asyncio

from ..db import SessionLocal
from ..services.withdraw import create_withdraw_request, check_withdraw_status
from ..repositories.withdrawals import WithdrawalsRepo
from ..repositories.users import UsersRepo

router = APIRouter(tags=["wallet"])

class WithdrawIn(BaseModel):
    user_id: int
    to_address: str
    amount: float
    # network: str

@router.post("/withdraw")
async def create_withdraw(req: WithdrawIn):
    async with SessionLocal() as db:
        repo = WithdrawalsRepo(db)
        users = UsersRepo(db)
        try:
            ton_amount = await convert_usd_to_ton(float(req.amount))
            # ton_amount = 0.101
            await users.add_balance(req.user_id, -1 * req.amount)
            result = await create_withdraw_request(ton_amount, req.to_address)
            wid = await repo.create(req.user_id, req.amount, req.to_address, "USDT")
            # asyncio.create_task(check_withdraw(db, wid, str(result), ton_amount, req.user_id, req.amount))
            return {"ok": True, "tx": result}
        # except WithdrawalLogicError as e:
        #     raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))
        
async def check_withdraw(s: AsyncSession, wid: int, tx_hash: str, ton_amount: float, uid: int, amount: float):
    await asyncio.sleep(300)

    success = await check_withdraw_status(tx_hash)

    repo = WithdrawalsRepo(s)
    await repo.mark_status(wid, 'sent' if success else 'failed', payload={"success": str(success), "in_ton": ton_amount, "tx_hash": tx_hash})

    users = UsersRepo(s)
    if not success:
        await users.add_balance(uid, amount)


# @router.post("/heleket/callback")
# async def heleket_callback(payload: HeleketWebhook, request: Request, db: AsyncSession = Depends(SessionLocal), x_heleket_signature: Optional[str] = Header(None)):
#     if not _verify_signature(request, x_heleket_signature):
#         raise HTTPException(status_code=401, detail="invalid signature")

#     try:
#         await apply_withdrawal_status(db, provider_id=payload.id, provider_status=payload.status, payload=payload.data or {})
#         return {"ok": True}
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=str(e))
