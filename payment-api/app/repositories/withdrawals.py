from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class WithdrawalsRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def create(self, user_id: int, amount: float, to_address: str, currency: str = "TON") -> int:
        q = text("""
            INSERT INTO withdrawals (user_id, amount, to_address, currency, status)
            VALUES (:uid, :amt, :addr, :cur, 'pending')
            RETURNING id
        """)
        rid = (await self.s.execute(q, {"uid": user_id, "amt": amount, "addr": to_address, "cur": currency})).scalar_one()
        await self.s.commit()
        return rid

    async def set_processing(self, wid: int, provider_id: str, payload: Dict[str, Any], fee: Optional[float] = None):
        q = text("""
            UPDATE withdrawals
               SET status='processing',
                   provider_id=:pid,
                   provider_payload = coalesce(provider_payload,'{}'::jsonb) || :payload::jsonb,
                   fee=:fee
             WHERE id=:wid
        """)
        await self.s.execute(q, {"wid": wid, "pid": provider_id, "payload": payload, "fee": fee})

    async def mark_status(self, wid: int, status: str, payload: Dict[str, Any]):
        q = text("""
            UPDATE withdrawals
               SET status=:st,
                   provider_payload = coalesce(provider_payload,'{}'::jsonb) || CAST(:payload AS jsonb),
                   processed_at = CASE WHEN :st IN ('sent','failed','canceled') THEN now() ELSE processed_at END
             WHERE id=:wid
        """)
        await self.s.execute(q, {"wid": wid, "st": status, "payload": payload})
        await self.s.commit()

    async def get_by_provider(self, provider_id: str) -> Optional[int]:
        q = text("SELECT id FROM withdrawals WHERE provider_id=:pid LIMIT 1")
        return (await self.s.execute(q, {"pid": provider_id})).scalar_one_or_none()
