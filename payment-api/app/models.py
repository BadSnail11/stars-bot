from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, String, Boolean, JSON, TIMESTAMP, ForeignKey, DECIMAL
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(Text())
    first_name: Mapped[str | None] = mapped_column(Text())
    last_name: Mapped[str | None] = mapped_column(Text())
    lang_code: Mapped[str | None] = mapped_column(String(8))
    balance: Mapped[float | None] = mapped_column(DECIMAL(18,6))
    accepted_offer_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False), nullable=True)
    # accepted_offer_at = mapped_column(TIMESTAMP(timezone=False), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

class RequiredChannel(Base):
    __tablename__ = "required_channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_username: Mapped[str] = mapped_column(Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str | None] = mapped_column(Text())
    recipient: Mapped[str | None] = mapped_column(Text())
    type: Mapped[str | None] = mapped_column(String(16))
    amount: Mapped[int | None] = mapped_column(BigInteger)
    price: Mapped[float | None] = mapped_column(DECIMAL(18,2))
    income: Mapped[float | None] = mapped_column(DECIMAL(18,2))
    currency: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str | None] = mapped_column(Text())
    gateway_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
    paid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_user_id: Mapped[int | None] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text())
    inline_keyboard: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

class PricingRule(Base):
    __tablename__ = "pricing_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_type: Mapped[str | None] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16))
    markup_percent: Mapped[float | None] = mapped_column(DECIMAL(8,3))
    manual_price: Mapped[float | None] = mapped_column(DECIMAL(18,6))
    currency: Mapped[str | None] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("user_bots.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger)
    referee_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))


class UserBot(Base):
    __tablename__ = "user_bots"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    tg_bot_token: Mapped[str | None] = mapped_column(String())
    bot_username: Mapped[str | None] = mapped_column(String())
    tg_bot_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)