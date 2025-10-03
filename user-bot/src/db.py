import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None

async def init_engine():
    global _engine, _session_maker
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    _engine = create_async_engine(db_url, pool_pre_ping=True)
    _session_maker = async_sessionmaker(_engine, expire_on_commit=False)

def get_session_maker() -> async_sessionmaker[AsyncSession]:
    assert _session_maker is not None, "Engine not initialized. Call init_engine() first."
    return _session_maker

async def close_engine():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
