import uvicorn
from fastapi import FastAPI
from .routers import orders, withdrawals
from contextlib import asynccontextmanager
from .redis import get_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    _ = await get_redis()
    yield
    # shutdown
    await close_redis()

app = FastAPI(title="Payment API", lifespan=lifespan)
app.include_router(orders.router)
app.include_router(withdrawals.router)
# app.include_router(callbacks.router)  # если используешь вебхуки

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=False)
