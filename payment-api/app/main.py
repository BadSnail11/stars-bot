import uvicorn
from fastapi import FastAPI
from .routers import orders

app = FastAPI(title="Payment API")
app.include_router(orders.router)
# app.include_router(callbacks.router)  # если используешь вебхуки

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=False)
