from typing import Optional
from sqlalchemy import select, update, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from ..models import User

class UsersRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_tg_id(self, tg_user_id: int) -> Optional[User]:
        q = select(User).where(User.tg_user_id == tg_user_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def upsert_from_telegram(self, tg_user) -> User:
        user = await self.get_by_tg_id(tg_user.id)
        if user is None:
            user = User(
                tg_user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                lang_code=getattr(tg_user, "language_code", None),
            )
            self.session.add(user)
            await self.session.flush()
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.lang_code = getattr(tg_user, "language_code", None)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_offer_accepted_now(self, tg_user_id: int):
        # # server-side NOW()
        # q = update(User).where(User.tg_user_id == tg_user_id).values(accepted_offer_at=text("NOW()"))
        # await self.session.execute(q)
        await self.session.execute(
            update(User)
            .where(User.tg_user_id == tg_user_id)
            .values(accepted_offer_at=func.now())  # безопаснее, чем text("NOW()")
        )
        await self.session.commit()

    async def add_balance(self, user_id: int, delta: float):
        # аккуратное инкрементирование DECIMAL
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(balance=User.balance + delta)
        )
        await self.session.commit()

    async def upsert_from_tg_payload(self, tg_user_id: int, username: str | None) -> User:
        stmt = pg_insert(User).values(
            tg_user_id=tg_user_id,
            username=username,
        ).on_conflict_do_update(
            index_elements=[User.tg_user_id],
            set_={"username": username}
        ).returning(User)
        res = await self.session.execute(stmt)
        user = res.scalar_one()
        await self.session.commit()
        return user