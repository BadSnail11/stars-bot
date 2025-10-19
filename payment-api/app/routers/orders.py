from fastapi import APIRouter, HTTPException
from ..schemas import CreateOrderRequest, CreateOrderResponse, OrderStatusResponse
from ..db import SessionLocal
from ..repositories.users import UsersRepo
from ..repositories.orders import OrdersRepo
from ..repositories.pricing import PricingRepo
from ..repositories.user_bots import UserBotsRepo
from ..services.pricing import (
    get_star_price_in_ton, calc_ton_for_stars,
    get_star_price_in_rub, calc_rub_for_stars,
    get_premium_price_in_ton, calc_ton_for_premium,
    get_premium_price_in_rub, calc_rub_for_premium,
    get_ton_price_in_ton, calc_ton_for_ton,
    get_ton_price_in_rub, calc_rub_for_ton
)
from ..services.ton import wait_ton_payment, generate_memo
from ..services.platega import create_sbp_invoice, wait_payment_confirmed
from ..services.fulfillment import fulfill_order
from ..services.referral_accrual import accrue_referral_reward
from ..services import heleket as hk
import os, asyncio
from decimal import Decimal
from ..services.heleket import wait_invoice_paid

# from ..services.fragment import get_prices


router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=CreateOrderResponse)
async def create_order(payload: CreateOrderRequest):
    async with SessionLocal() as session:
        users = UsersRepo(session)
        orders = OrdersRepo(session)
        user_bots = UserBotsRepo(session)

        user = await users.get_by_tg_id(payload.user_tg_id)

        bot_tg_id = payload.bot_tg_id
        bot = await UserBotsRepo.get_by_tg_bot_id(user_bots, bot_tg_id)
        bot_id = bot.id

        # ветвим по типу и способу оплаты
        if payload.order_type == "stars":
            qty = int(payload.amount)
            if qty < 50:
                raise HTTPException(400, "Минимум 50 звёзд")
            if payload.payment_method == "TON":
                price_per_star_ton = await get_star_price_in_ton(session, bot_id)
                total_ton = calc_ton_for_stars(qty, price_per_star_ton)
                wallet = os.getenv("TON_WALLET")
                if not wallet:
                    raise HTTPException(500, "TON_WALLET not configured")
                # memo = f"{os.getenv('TON_MEMO_PREFIX','INV-')}{payload.user_tg_id}"
                order = await orders.create_pending_ton_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=qty,
                    price=float(total_ton),
                    memo="",
                    wallet=wallet
                )
                order_id = str(order.id)
                memo = await generate_memo(os.getenv('TON_MEMO_PREFIX','INV-'), order_id, str(user.tg_user_id))
                await orders.change_memo(order.id, payload.order_type, qty, memo, wallet, payload.recipient)
                # запустим фоновую проверку TON
                asyncio.create_task(_background_ton_check(order.id, wallet, memo, total_ton, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    ton={"address": wallet, "memo": memo, "amount_ton": str(total_ton)}
                )

            elif payload.payment_method == "SBP":
                price_per_star_rub = await get_star_price_in_rub(session, bot_id)
                amount_rub = calc_rub_for_stars(qty, price_per_star_rub)
                tx_id, redirect = await create_sbp_invoice(
                    amount_rub=amount_rub,
                    description=f"Покупка {qty}⭐",
                    payload=f"user:{payload.user_tg_id}|stars:{qty}"
                )
                order = await orders.create_pending_sbp_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=qty,
                    price=amount_rub,
                    transaction_id=tx_id,
                    redirect_url=redirect
                )
                # фоновый пуллинг статуса
                asyncio.create_task(_background_sbp_check(order.id, tx_id, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    sbp={"redirect_url": redirect, "transaction_id": tx_id, "amount_rub": amount_rub}
                )
            elif payload.payment_method == "CRYPTO_OTHER":
                # RUB-прайс → передаём в Heleket, он сконвертит в USDT TRC20
                price_per_star_rub = await get_star_price_in_rub(session, bot_id)
                amount_rub = calc_rub_for_stars(qty, price_per_star_rub)

                # создаём pending-заказ в нашей БД
                order = await orders.create_pending_other_crypto_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=qty,
                    price=amount_rub
                )


                inv = await hk.create_invoice(
                    amount=f"{amount_rub:.2f}",
                    currency="RUB",
                    order_id=str(order.id),   # важно: уникальный,
                    user_tg_id=str(payload.user_tg_id),
                    # to_currency="USDT",
                    # network=os.getenv("HELEKET_PAYER_NETWORK","tron"),
                    # url_return=os.getenv("HELEKET_RETURN_URL"),
                    # url_success=os.getenv("HELEKET_SUCCESS_URL"),
                    url_callback=os.getenv("HELEKET_CALLBACK_URL"),
                    lifetime=int(os.getenv("HELEKET_INVOICE_LIFETIME","1800")),
                )

                # сохраним полезное в gateway_payload
                await orders.update_gateway_payload(order.id, {
                    "provider": "heleket",
                    "heleket": {
                        "uuid": inv.get("result", {}).get("uuid"),
                        "url": inv.get("result", {}).get("url"),
                        "address": inv.get("result", {}).get("address"),
                        "payer_currency": inv.get("result", {}).get("payer_currency"),
                        "network": inv.get("result", {}).get("network"),
                    }
                })

                # запустим фоновый пуллинг статуса (если не пользуешься вебхуком)
                asyncio.create_task(_background_heleket_check(order.id, user.tg_user_id, bot_id))

                return CreateOrderResponse(
                    order_id=order.id,
                    status=order.status,
                    other={"redirect_url": inv.get("result", {}).get("url"), "transaction_id": inv.get("result", {}).get("uuid"), "amount_rub": amount_rub},
                    message="Оплатите по ссылке Heleket",
                )

            else:
                raise HTTPException(400, "Способ оплаты не поддержан (other)")

        elif payload.order_type == "premium":
            months = int(payload.amount)
            if months not in (3,6,12):
                raise HTTPException(400, "Premium: допускаются только 3/6/12 мес.")
            if payload.payment_method == "TON":
                price_per_month_ton = await get_premium_price_in_ton(session, bot_id)
                total_ton = calc_ton_for_premium(months, price_per_month_ton)
                wallet = os.getenv("TON_WALLET")
                if not wallet:
                    raise HTTPException(500, "TON_WALLET not configured")
                # memo = f"{os.getenv('TON_MEMO_PREFIX','INV-')}P-{payload.user_tg_id}"
                order = await orders.create_pending_ton_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.payment_method,
                    amount=months,
                    price=float(total_ton),
                    memo="",
                    wallet=wallet
                )
                order_id = str(order.id)
                memo = await generate_memo(os.getenv('TON_MEMO_PREFIX','INV-'), order_id, str(user.tg_user_id))
                await orders.change_memo(order.id, payload.order_type, months, memo, wallet, payload.recipient)
                asyncio.create_task(_background_ton_check(order.id, wallet, memo, total_ton, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    ton={"address": wallet, "memo": memo, "amount_ton": str(total_ton)}
                )

            elif payload.payment_method == "SBP":
                price_per_month_rub = await get_premium_price_in_rub(session, bot_id)
                amount_rub = calc_rub_for_premium(months, price_per_month_rub)
                tx_id, redirect = await create_sbp_invoice(
                    amount_rub=amount_rub,
                    description=f"Telegram Premium {months} мес.",
                    payload=f"user:{payload.user_tg_id}|premium:{months}"
                )
                order = await orders.create_pending_sbp_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=float(months),
                    price=amount_rub,
                    transaction_id=tx_id,
                    redirect_url=redirect
                )
                asyncio.create_task(_background_sbp_check(order.id, tx_id, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    sbp={"redirect_url": redirect, "transaction_id": tx_id, "amount_rub": amount_rub}
                )
            elif payload.payment_method == "HELEKET":
                price_per_month_rub = await get_premium_price_in_rub(session)
                amount_rub = calc_rub_for_premium(months, price_per_month_rub)

                order = await orders.create_pending_other_crypto_order(
                    user_id=user.id, username=user.username,
                    months=months, recipient=payload.recipient,
                    amount=amount_rub, currency="RUB",
                    provider="heleket", type="premium"
                )

                inv = await hk.create_invoice(
                    amount=f"{amount_rub:.2f}",
                    currency="RUB",
                    order_id=str(order.id),
                    # to_currency="USDT",
                    user_tg_id=user.tg_user_id,
                    # network=os.getenv("HELEKET_PAYER_NETWORK","tron"),
                    # url_return=os.getenv("HELEKET_RETURN_URL"),
                    # url_success=os.getenv("HELEKET_SUCCESS_URL"),
                    url_callback=os.getenv("HELEKET_CALLBACK_URL"),
                    lifetime=int(os.getenv("HELEKET_INVOICE_LIFETIME","1800")),
                )

                await orders.update_gateway_payload(order.id, {
                    "provider": "heleket",
                    "heleket": {
                        "uuid": inv.get("result", {}).get("uuid"),
                        "url": inv.get("result", {}).get("url"),
                        "address": inv.get("result", {}).get("address"),
                        "payer_currency": inv.get("result", {}).get("payer_currency"),
                        "network": inv.get("result", {}).get("network"),
                    }
                })

                asyncio.create_task(_background_heleket_check(order.id, user.tg_user_id))

                return CreateOrderResponse(
                    order_id=order.id,
                    status=order.status,
                    other={"redirect_url": inv.get("result", {}).get("url"), "transaction_id": inv.get("result", {}).get("uuid"), "amount_rub": amount_rub},
                    message="Оплатите по ссылке Heleket",
                )

            else:
                raise HTTPException(400, "Способ оплаты не поддержан (other)")
        elif payload.order_type == "ton":
            amount = int(payload.amount)
            if payload.payment_method == "TON":
                # price_per_star_ton = await get_star_price_in_ton(session, bot_id)
                ton_price = await get_ton_price_in_ton(session, bot_id)
                total_ton = calc_ton_for_ton(amount, ton_price)
                wallet = os.getenv("TON_WALLET")
                if not wallet:
                    raise HTTPException(500, "TON_WALLET not configured")
                # memo = f"{os.getenv('TON_MEMO_PREFIX','INV-')}{payload.user_tg_id}"
                order = await orders.create_pending_ton_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=amount,
                    price=float(total_ton),
                    memo="",
                    wallet=wallet
                )
                order_id = str(order.id)
                memo = await generate_memo(os.getenv('TON_MEMO_PREFIX','INV-'), order_id, str(user.tg_user_id))
                await orders.change_memo(order.id, payload.order_type, amount, memo, wallet, payload.recipient)
                # запустим фоновую проверку TON
                asyncio.create_task(_background_ton_check(order.id, wallet, memo, total_ton, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    ton={"address": wallet, "memo": memo, "amount_ton": str(total_ton)}
                )

            elif payload.payment_method == "SBP":
                price_per_ton_rub = await get_ton_price_in_rub(session, bot_id)
                amount_rub = calc_rub_for_ton(amount, price_per_ton_rub)
                tx_id, redirect = await create_sbp_invoice(
                    amount_rub=amount_rub,
                    description=f"Покупка {amount} TON",
                    payload=f"user:{payload.user_tg_id}|TON:{amount}"
                )
                order = await orders.create_pending_sbp_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=amount,
                    price=amount_rub,
                    transaction_id=tx_id,
                    redirect_url=redirect
                )
                # фоновый пуллинг статуса
                asyncio.create_task(_background_sbp_check(order.id, tx_id, bot_id))
                return CreateOrderResponse(
                    order_id=order.id, status=order.status,
                    sbp={"redirect_url": redirect, "transaction_id": tx_id, "amount_rub": amount_rub}
                )
            elif payload.payment_method == "CRYPTO_OTHER":
                # RUB-прайс → передаём в Heleket, он сконвертит в USDT TRC20
                price_per_ton_rub = await get_ton_price_in_rub(session, bot_id)
                amount_rub = calc_rub_for_ton(amount, price_per_star_rub)

                # создаём pending-заказ в нашей БД
                order = await orders.create_pending_other_crypto_order(
                    user_id=user.id,
                    username=user.username,
                    recipient=payload.recipient,
                    type=payload.order_type,
                    amount=amount,
                    price=amount_rub
                )


                inv = await hk.create_invoice(
                    amount=f"{amount_rub:.2f}",
                    currency="RUB",
                    order_id=str(order.id),   # важно: уникальный,
                    user_tg_id=str(payload.user_tg_id),
                    # to_currency="USDT",
                    # network=os.getenv("HELEKET_PAYER_NETWORK","tron"),
                    # url_return=os.getenv("HELEKET_RETURN_URL"),
                    # url_success=os.getenv("HELEKET_SUCCESS_URL"),
                    url_callback=os.getenv("HELEKET_CALLBACK_URL"),
                    lifetime=int(os.getenv("HELEKET_INVOICE_LIFETIME","1800")),
                )

                # сохраним полезное в gateway_payload
                await orders.update_gateway_payload(order.id, {
                    "provider": "heleket",
                    "heleket": {
                        "uuid": inv.get("result", {}).get("uuid"),
                        "url": inv.get("result", {}).get("url"),
                        "address": inv.get("result", {}).get("address"),
                        "payer_currency": inv.get("result", {}).get("payer_currency"),
                        "network": inv.get("result", {}).get("network"),
                    }
                })

                # запустим фоновый пуллинг статуса (если не пользуешься вебхуком)
                asyncio.create_task(_background_heleket_check(order.id, user.tg_user_id, bot_id))

                return CreateOrderResponse(
                    order_id=order.id,
                    status=order.status,
                    other={"redirect_url": inv.get("result", {}).get("url"), "transaction_id": inv.get("result", {}).get("uuid"), "amount_rub": amount_rub},
                    message="Оплатите по ссылке Heleket",
                )

            else:
                raise HTTPException(400, "Способ оплаты не поддержан (other)")
        else:
            raise HTTPException(400, "Unknown order_type")
        
        


@router.get("/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(order_id: int):
    async with SessionLocal() as session:
        orders = OrdersRepo(session)
        order = await orders.get_by_id(order_id)
        if not order:
            raise HTTPException(404, "Order not found")
        return OrderStatusResponse(order_id=order.id, status=order.status, message=order.message or None)


# ==== фоновые операции ====

async def _on_paid(order_id: int, tx_hash: str | None, bot_id: int):
    async with SessionLocal() as session:
        orders = OrdersRepo(session)
        order = await orders.get_by_id(order_id)
        if not order or order.status == "paid":
            return
        await orders.mark_paid(order_id, tx_hash or "n/a", income=None)

        # Рефералка
        fresh = await orders.get_by_id(order_id)
        from ..services.referral_accrual import accrue_referral_reward
        await accrue_referral_reward(session, fresh, bot_id)

        # Фулфилмент через Fragment
        from ..services.fulfillment import fulfill_order
        ok, msg = await fulfill_order(session, fresh)

async def _background_ton_check(order_id: int, wallet: str, memo: str, total_ton: Decimal, bot_id: int):
    tx_hash = await wait_ton_payment(wallet, memo, total_ton)
    if tx_hash:
        await _on_paid(order_id, tx_hash, bot_id)

async def _background_sbp_check(order_id: int, tx_id: str, bot_id):
    status_tx = await wait_payment_confirmed(tx_id)
    if status_tx:
        await _on_paid(order_id, status_tx, bot_id)


async def _background_heleket_check(order_id: int, user_tg_id: int, bot_id: int):
    res = await wait_invoice_paid(order_id=str(order_id), user_tg_id=str(user_tg_id), poll_interval=10)
    if res:
        await _on_paid(order_id, res.get("txid"), bot_id)




# @router.post("/test")
# async def create_order_test():
#     # return await _on_paid(57, "19bc4910dbd5a0345fb39216c1134fbb6a6dd3ecbe0ec7f2682e5fb74afee67c", 1)
#     return await _on_paid(30, "19bc4910dbd5a0345fb39216c1134fbb6a6dd3ecbe0ec7f2682e5fb74afee67c", 12)