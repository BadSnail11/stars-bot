import asyncio
from typing import Callable, Awaitable, Optional
from .payments_api import get_order_status

async def poll_until_paid(
    order_id: int,
    *,
    on_paid: Callable[[dict], Awaitable[None]],
    on_timeout: Callable[[], Awaitable[None]],
    interval_sec: float = 5.0,
    timeout_sec: float = 15 * 60
):
    deadline = asyncio.get_event_loop().time() + timeout_sec
    while asyncio.get_event_loop().time() < deadline:
        data = await get_order_status(order_id)
        if data.get("status") == "paid":
            await on_paid(data)
            return
        await asyncio.sleep(interval_sec)
    await on_timeout()
