from pydantic import BaseModel, Field
from typing import Literal, Optional

PaymentMethod = Literal["TON", "SBP", "CRYPTO_OTHER"]
OrderType = Literal["stars", "premium", "ton"]

class CreateOrderRequest(BaseModel):
    user_tg_id: int
    username: Optional[str] = None
    recipient: Optional[str] = None
    order_type: OrderType
    amount: int  # звёзды (шт) или премиум (мес)
    payment_method: PaymentMethod
    bot_tg_id: int

class TonPaymentInfo(BaseModel):
    address: str
    memo: str
    amount_ton: str

class SbpPaymentInfo(BaseModel):
    redirect_url: str
    transaction_id: str
    amount_rub: int

class OtherPaymentInfo(BaseModel):
    redirect_url: str
    transaction_id: str
    amount_rub: int

class CreateOrderResponse(BaseModel):
    order_id: int
    status: Literal["pending", "paid", "failed"]
    ton: Optional[TonPaymentInfo] = None
    sbp: Optional[SbpPaymentInfo] = None
    other: Optional[OtherPaymentInfo] = None
    message: Optional[str] = None

class OrderStatusResponse(BaseModel):
    order_id: int
    status: Literal["pending", "paid", "failed"]
    message: Optional[str] = None
