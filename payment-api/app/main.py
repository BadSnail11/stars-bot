import uvicorn
from fastapi import FastAPI
from .routers import orders, withdrawals
from contextlib import asynccontextmanager
from .redis import get_redis
import asyncio
from multiprocessing import Process
from .services.pricing import update_ton_price
from rq import Worker, Queue

@asynccontextmanager
async def lifespan(app: FastAPI):

    task = asyncio.create_task(update_ton_price())

    yield

    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Payment API", lifespan=lifespan)
app.include_router(orders.router)
app.include_router(withdrawals.router)
# app.include_router(callbacks.router)  # если используешь вебхуки

def start_worker():
    redis = asyncio.run(get_redis())
    q = Queue(connection=redis)
    worker = Worker([q])
    worker.work()

if __name__ == "__main__":
    p = Process(target=start_worker)
    p.start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=False)
